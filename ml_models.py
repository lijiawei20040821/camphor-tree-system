import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from scipy import stats
import joblib
import os

try:
    from config import config as flask_config
    _cfg = flask_config.get('default')
    RANDOM_SEED = _cfg.RANDOM_SEED
    GROWTH_MODEL_CFG = _cfg.GROWTH_MODEL
    CARBON_MODEL_CFG = _cfg.CARBON_MODEL
    FEATURE_ENG_CFG = _cfg.FEATURE_ENGINEERING
except Exception:
    RANDOM_SEED = 42
    GROWTH_MODEL_CFG = {
        'small_sample_params': {'n_estimators': 50, 'max_depth': 4, 'min_samples_split': 2, 'min_samples_leaf': 2},
        'medium_sample_params': {'n_estimators': 100, 'max_depth': 8, 'min_samples_split': 2, 'min_samples_leaf': 1},
        'large_sample_params': {'n_estimators': 200, 'max_depth': 15, 'min_samples_split': 2, 'min_samples_leaf': 1},
        'small_threshold': 20, 'medium_threshold': 100,
        'cv_min_samples': 6, 'cv_folds': 3, 'test_min_samples': 10, 'test_size': 0.2,
    }
    CARBON_MODEL_CFG = {
        'small_sample_params': {'n_estimators': 50, 'max_depth': 3, 'learning_rate': 0.1, 'min_samples_split': 2, 'min_samples_leaf': 2, 'subsample': 0.8},
        'medium_sample_params': {'n_estimators': 150, 'max_depth': 5, 'learning_rate': 0.1, 'min_samples_split': 2, 'min_samples_leaf': 1, 'subsample': 0.8},
        'large_sample_params': {'n_estimators': 300, 'max_depth': 6, 'learning_rate': 0.1, 'min_samples_split': 2, 'min_samples_leaf': 1, 'subsample': 0.8},
        'small_threshold': 20, 'medium_threshold': 100,
        'cv_min_samples': 6, 'cv_folds': 3, 'test_min_samples': 10, 'test_size': 0.2,
    }
    FEATURE_ENG_CFG = {
        'growth_features': ['total_precipitation', 'avg_humidity', 'avg_wind_speed', 'altitude', 'tree_height', 'carbon_per_age', 'hydro_thermal_index', 'wind_altitude_interaction', 'basal_area', 'heat_humidity_index'],
        'carbon_features': ['tree_age', 'dbh', 'tree_height', 'soil_compactness_encoded', 'avg_humidity', 'basal_area', 'slenderness_ratio', 'carbon_age_ratio'],
        'soil_mapping': {'疏松': 0, '中等': 1, '紧密': 2, '较疏松': 0},
    }


class CamphorTreeFeatureEngineer:
    """华南樟树生态特征工程：构造水热指数、风海拔交互、胸高断面积等专属特征"""

    def __init__(self):
        self.fitted = False

    def fit_transform(self, df):
        features = df.copy()
        features = self._add_derived_features(features)
        self.fitted = True
        return features

    def transform(self, df):
        if not self.fitted:
            raise RuntimeError("FeatureEngineer未fit，无法transform")
        features = df.copy()
        features = self._add_derived_features(features)
        return features

    def _add_derived_features(self, df):
        if 'total_precipitation' in df.columns and 'avg_humidity' in df.columns:
            df['hydro_thermal_index'] = (
                df['total_precipitation'] * df['avg_humidity'] / 100.0
            )

        if 'avg_wind_speed' in df.columns and 'altitude' in df.columns:
            df['wind_altitude_interaction'] = (
                df['avg_wind_speed'] * df['altitude']
            )

        if 'dbh' in df.columns:
            df['basal_area'] = np.pi * (df['dbh'] / 200.0) ** 2

        if 'tree_height' in df.columns and 'dbh' in df.columns:
            df['slenderness_ratio'] = df['tree_height'] / (df['dbh'] / 100.0)

        if 'avg_temperature' in df.columns and 'total_precipitation' in df.columns:
            df['temp_precip_ratio'] = df['avg_temperature'] / (
                df['total_precipitation'] + 1
            )

        if 'tree_age' in df.columns and 'annual_carbon_seq' in df.columns:
            df['carbon_age_ratio'] = df['annual_carbon_seq'] / (df['tree_age'] + 1)

        if 'avg_humidity' in df.columns and 'avg_temperature' in df.columns:
            df['heat_humidity_index'] = (
                df['avg_temperature'] * (100 - df['avg_humidity']) / 100.0
            )

        return df

    def get_feature_names(self):
        return [
            'hydro_thermal_index',
            'wind_altitude_interaction',
            'basal_area',
            'slenderness_ratio',
            'temp_precip_ratio',
            'carbon_age_ratio',
            'heat_humidity_index',
        ]

    def save(self, filepath):
        try:
            joblib.dump(
                {'fitted': self.fitted}, filepath
            )
            return True
        except Exception as e:
            print(f"保存特征工程器错误: {e}")
            return False

    def load(self, filepath):
        try:
            if os.path.exists(filepath):
                data = joblib.load(filepath)
                self.fitted = data['fitted']
                return True
            return False
        except Exception as e:
            print(f"加载特征工程器错误: {e}")
            return False


class GrowthStatusModel:
    """生长状态分类模型：RandomForestClassifier，支持特征工程和模型持久化"""

    def __init__(self):
        self.model = None
        self.label_encoder = LabelEncoder()
        self.feature_engineer = CamphorTreeFeatureEngineer()
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.feature_columns = FEATURE_ENG_CFG['growth_features']
        self.cfg = GROWTH_MODEL_CFG

    def _select_rf_params(self, n_samples):
        if n_samples < self.cfg['small_threshold']:
            return dict(self.cfg['small_sample_params'])
        elif n_samples < self.cfg['medium_threshold']:
            return dict(self.cfg['medium_sample_params'])
        else:
            return dict(self.cfg['large_sample_params'])

    def train(self, X, y):
        try:
            if isinstance(X, pd.DataFrame):
                X_fe = self.feature_engineer.fit_transform(X)
                X_fe = X_fe.reindex(columns=self.feature_columns, fill_value=0)
                X_scaled = self.scaler.fit_transform(X_fe)
            else:
                X_arr = np.array(X, dtype=float)
                X_fe = self._engineer_array(X_arr)
                X_scaled = self.scaler.fit_transform(X_fe)

            y_encoded = self.label_encoder.fit_transform(y)
            n_samples = len(X_scaled)
            params = self._select_rf_params(n_samples)

            self.model = RandomForestClassifier(
                **params, random_state=RANDOM_SEED, n_jobs=-1
            )

            note = None
            if n_samples < self.cfg['small_threshold']:
                note = '小样本(<20)训练，自适应降参，指标仅供参考'

            cv_mean = None
            cv_min = self.cfg['cv_min_samples']
            if n_samples >= cv_min and len(set(y_encoded)) >= 2:
                min_class_count = min(np.bincount(y_encoded))
                cv_folds = min(self.cfg['cv_folds'], n_samples, min_class_count)
                if cv_folds >= 2:
                    try:
                        cv_scores = cross_val_score(
                            self.model, X_scaled, y_encoded, cv=cv_folds, scoring='accuracy'
                        )
                        cv_mean = round(float(np.mean(cv_scores)), 4)
                    except Exception:
                        pass

            if n_samples >= self.cfg['test_min_samples']:
                X_train, X_test, y_train, y_test = train_test_split(
                    X_scaled, y_encoded, test_size=self.cfg['test_size'], random_state=RANDOM_SEED
                )
                self.model.fit(X_train, y_train)
                self.is_fitted = True
                train_acc = accuracy_score(y_train, self.model.predict(X_train))
                test_acc = accuracy_score(y_test, self.model.predict(X_test))
                result = {
                    'accuracy': round(test_acc, 4),
                    'train_accuracy': round(train_acc, 4),
                    'test_accuracy': round(test_acc, 4),
                    'cv_accuracy': cv_mean,
                    'n_samples': n_samples,
                    'params_used': params,
                }
            else:
                self.model.fit(X_scaled, y_encoded)
                self.is_fitted = True
                acc = accuracy_score(y_encoded, self.model.predict(X_scaled))
                result = {
                    'accuracy': round(acc, 4),
                    'cv_accuracy': cv_mean,
                    'n_samples': n_samples,
                    'params_used': params,
                }

            if note:
                result['note'] = note
            return result
        except Exception as e:
            print(f"生长模型训练错误: {e}")
            return {'accuracy': 0}

    def predict(self, features):
        try:
            if self.model is None or not self.is_fitted:
                return self._fallback_predict(features)

            if isinstance(features, pd.DataFrame):
                X_fe = self.feature_engineer.transform(features)
                X_fe = X_fe.reindex(columns=self.feature_columns, fill_value=0)
            else:
                feat_arr = np.array(features, dtype=float).reshape(1, -1)
                X_fe = self._engineer_array(feat_arr)

            X_scaled = self.scaler.transform(X_fe)
            pred_encoded = self.model.predict(X_scaled)
            probas = self.model.predict_proba(X_scaled)
            confidence = round(float(np.max(probas, axis=1)[0]), 2)
            label = self.label_encoder.inverse_transform(pred_encoded)[0]
            return str(label), confidence
        except Exception as e:
            print(f"生长预测错误: {e}")
            return self._fallback_predict(features)

    def _fallback_predict(self, features):
        if isinstance(features, list):
            precipitation = features[0] if len(features) > 0 else 1600
            humidity = features[1] if len(features) > 1 else 75
            wind_speed = features[2] if len(features) > 2 else 2.0
            altitude = features[3] if len(features) > 3 else 50
            tree_height = features[4] if len(features) > 4 else 15
            carbon_per_age = features[5] if len(features) > 5 else 0.5
        else:
            precipitation, humidity, wind_speed, altitude, tree_height, carbon_per_age = (
                1600, 75, 2.0, 50, 15, 0.5
            )

        score = 0
        if precipitation > 1600:
            score += 1
        if humidity > 75:
            score += 1
        if wind_speed < 2.5:
            score += 1
        if altitude < 100:
            score += 1
        if tree_height > 10:
            score += 1
        if carbon_per_age > 0.5:
            score += 1

        if score >= 4:
            return '正常', 0.85
        elif score >= 2:
            return '衰弱', 0.70
        else:
            return '濒危', 0.60

    def _engineer_array(self, X):
        X_fe = np.zeros((X.shape[0], len(self.feature_columns)))
        col_map = {
            'total_precipitation': 0,
            'avg_humidity': 1,
            'avg_wind_speed': 2,
            'altitude': 3,
            'tree_height': 4,
            'carbon_per_age': 5,
        }
        for name, idx in col_map.items():
            if idx < X.shape[1]:
                X_fe[:, idx] = X[:, idx]

        prec = X_fe[:, 0]
        hum = X_fe[:, 1]
        wind = X_fe[:, 2]
        alt = X_fe[:, 3]
        height = X_fe[:, 4]

        X_fe[:, 6] = prec * hum / 100.0
        X_fe[:, 7] = wind * alt
        dbh_est = np.maximum(height * 8, 30)
        X_fe[:, 8] = np.pi * (dbh_est / 200.0) ** 2
        temp_est = 22.0
        X_fe[:, 9] = temp_est * (100 - hum) / 100.0

        return X_fe

    def save(self, filepath):
        try:
            joblib.dump({
                'model': self.model,
                'label_encoder': self.label_encoder,
                'scaler': self.scaler,
                'feature_engineer': self.feature_engineer,
                'is_fitted': self.is_fitted,
                'feature_columns': self.feature_columns,
            }, filepath)
            return True
        except Exception as e:
            print(f"保存生长模型错误: {e}")
            return False

    def load(self, filepath):
        try:
            if os.path.exists(filepath):
                data = joblib.load(filepath)
                self.model = data['model']
                self.label_encoder = data['label_encoder']
                self.scaler = data.get('scaler', StandardScaler())
                self.feature_engineer = data.get('feature_engineer', CamphorTreeFeatureEngineer())
                self.is_fitted = data['is_fitted']
                self.feature_columns = data.get('feature_columns', self.feature_columns)
                return True
            return False
        except Exception as e:
            print(f"加载生长模型错误: {e}")
            return False


class CarbonSequestrationModel:
    """碳汇量回归模型：GradientBoostingRegressor，输出评估指标"""

    def __init__(self):
        self.model = None
        self.is_fitted = False
        self.feature_columns = FEATURE_ENG_CFG['carbon_features']
        self.soil_mapping = FEATURE_ENG_CFG['soil_mapping']
        self.cfg = CARBON_MODEL_CFG
        self.metrics = {}

    def _select_gbr_params(self, n_samples):
        if n_samples < self.cfg['small_threshold']:
            return dict(self.cfg['small_sample_params'])
        elif n_samples < self.cfg['medium_threshold']:
            return dict(self.cfg['medium_sample_params'])
        else:
            return dict(self.cfg['large_sample_params'])

    def train(self, X, y):
        try:
            X_fe = self._prepare_features(X)
            n_samples = len(X_fe)
            params = self._select_gbr_params(n_samples)

            self.model = GradientBoostingRegressor(
                **params, random_state=RANDOM_SEED
            )

            note = None
            if n_samples < self.cfg['small_threshold']:
                note = '小样本(<20)训练，自适应降参，指标仅供参考'

            cv_r2_mean = None
            cv_rmse_mean = None
            cv_min = self.cfg['cv_min_samples']
            if n_samples >= cv_min:
                cv_folds = min(self.cfg['cv_folds'], n_samples)
                if cv_folds >= 2:
                    try:
                        cv_r2 = cross_val_score(
                            self.model, X_fe, y, cv=cv_folds, scoring='r2'
                        )
                        cv_mse = -cross_val_score(
                            self.model, X_fe, y, cv=cv_folds, scoring='neg_mean_squared_error'
                        )
                        cv_r2_mean = round(float(np.mean(cv_r2)), 4)
                        cv_rmse_mean = round(float(np.sqrt(np.mean(cv_mse))), 4)
                    except Exception:
                        pass

            if n_samples >= self.cfg['test_min_samples']:
                X_train, X_test, y_train, y_test = train_test_split(
                    X_fe, y, test_size=self.cfg['test_size'], random_state=RANDOM_SEED
                )
                self.model.fit(X_train, y_train)
                self.is_fitted = True
                y_train_pred = self.model.predict(X_train)
                y_test_pred = self.model.predict(X_test)
                self.metrics = {
                    'rmse': round(float(np.sqrt(mean_squared_error(y_test, y_test_pred))), 4),
                    'mae': round(float(mean_absolute_error(y_test, y_test_pred)), 4),
                    'r2': round(float(r2_score(y_test, y_test_pred)), 4),
                    'train_r2': round(float(r2_score(y_train, y_train_pred)), 4),
                    'test_r2': round(float(r2_score(y_test, y_test_pred)), 4),
                    'cv_r2': cv_r2_mean,
                    'cv_rmse': cv_rmse_mean,
                    'n_samples': n_samples,
                    'params_used': params,
                }
            else:
                self.model.fit(X_fe, y)
                self.is_fitted = True
                y_pred = self.model.predict(X_fe)
                self.metrics = {
                    'rmse': round(float(np.sqrt(mean_squared_error(y, y_pred))), 4),
                    'mae': round(float(mean_absolute_error(y, y_pred)), 4),
                    'r2': round(float(r2_score(y, y_pred)), 4),
                    'cv_r2': cv_r2_mean,
                    'cv_rmse': cv_rmse_mean,
                    'n_samples': n_samples,
                    'params_used': params,
                }

            if note:
                self.metrics['note'] = note
            return self.metrics
        except Exception as e:
            print(f"碳汇模型训练错误: {e}")
            return {}

    def predict(self, features):
        try:
            if self.model is None or not self.is_fitted:
                return self._fallback_predict(features)

            X_fe = self._prepare_features(features)
            pred = self.model.predict(X_fe)
            val = float(pred[0]) if hasattr(pred, '__len__') else float(pred)
            return max(round(val, 2), 10.0)
        except Exception as e:
            print(f"碳汇预测错误: {e}")
            return self._fallback_predict(features)

    def _fallback_predict(self, features):
        if isinstance(features, list):
            tree_age = features[0] if len(features) > 0 else 150
            dbh = features[1] if len(features) > 1 else 120
            tree_height = features[2] if len(features) > 2 else 15
            soil_compactness = features[3] if len(features) > 3 else '中等'
            humidity = features[4] if len(features) > 4 else 75
        else:
            tree_age, dbh, tree_height, soil_compactness, humidity = (
                150, 120, 15, '中等', 75
            )

        base_carbon = dbh * tree_height * 0.1
        soil_val = self.soil_mapping.get(str(soil_compactness), 1)
        if soil_val == 0:
            base_carbon *= 1.2
        elif soil_val == 2:
            base_carbon *= 0.8

        if humidity > 80:
            base_carbon *= 1.1
        elif humidity < 60:
            base_carbon *= 0.9

        return max(round(base_carbon, 2), 10.0)

    def _prepare_features(self, features):
        if isinstance(features, list):
            arr = np.zeros((1, len(self.feature_columns)))
            numeric_idx = [0, 1, 2, 4]
            for i, idx in enumerate(numeric_idx):
                if idx < len(features):
                    try:
                        arr[0, idx] = float(features[idx])
                    except (ValueError, TypeError):
                        arr[0, idx] = 0.0

            soil_raw = features[3] if len(features) > 3 else '中等'
            if isinstance(soil_raw, str):
                arr[0, 3] = self.soil_mapping.get(soil_raw, 1)
            else:
                try:
                    arr[0, 3] = float(soil_raw)
                except (ValueError, TypeError):
                    arr[0, 3] = 1.0

            arr[0, 5] = np.pi * (arr[0, 1] / 200.0) ** 2
            arr[0, 6] = arr[0, 2] / (arr[0, 1] / 100.0 + 1)
            estimated_carbon = arr[0, 1] * arr[0, 2] * 0.1
            arr[0, 7] = estimated_carbon / (arr[0, 0] + 1)

            return arr

        elif isinstance(features, pd.DataFrame):
            X = features.copy()
            if 'soil_compactness' in X.columns:
                X['soil_compactness_encoded'] = X['soil_compactness'].map(
                    self.soil_mapping
                ).fillna(1)
            else:
                X['soil_compactness_encoded'] = 1

            if 'dbh' in X.columns:
                X['basal_area'] = np.pi * (X['dbh'] / 200.0) ** 2
            else:
                X['basal_area'] = 0

            if 'tree_height' in X.columns and 'dbh' in X.columns:
                X['slenderness_ratio'] = X['tree_height'] / (X['dbh'] / 100.0 + 1)
            else:
                X['slenderness_ratio'] = 0

            if 'annual_carbon_seq' in X.columns and 'tree_age' in X.columns:
                X['carbon_age_ratio'] = X['annual_carbon_seq'] / (X['tree_age'] + 1)
            else:
                X['carbon_age_ratio'] = 0

            for col in self.feature_columns:
                if col not in X.columns:
                    X[col] = 0

            return X[self.feature_columns].values

        else:
            arr = np.array(features, dtype=float)
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            return arr

    def save(self, filepath):
        try:
            joblib.dump({
                'model': self.model,
                'is_fitted': self.is_fitted,
                'metrics': self.metrics,
                'soil_mapping': self.soil_mapping,
                'feature_columns': self.feature_columns,
            }, filepath)
            return True
        except Exception as e:
            print(f"保存碳汇模型错误: {e}")
            return False

    def load(self, filepath):
        try:
            if os.path.exists(filepath):
                data = joblib.load(filepath)
                self.model = data['model']
                self.is_fitted = data['is_fitted']
                self.metrics = data.get('metrics', {})
                self.soil_mapping = data.get('soil_mapping', self.soil_mapping)
                self.feature_columns = data.get('feature_columns', self.feature_columns)
                return True
            return False
        except Exception as e:
            print(f"加载碳汇模型错误: {e}")
            return False


class EcologicalCorrelationAnalyzer:
    """生态因子关联分析：Pearson/Spearman相关 + 变异系数 + 主导因子分析"""

    def __init__(self):
        self.results = {}

    def _correlation_analysis(self, method_name, corr_func, x, y):
        """相关性分析公共方法"""
        try:
            corr, p_value = corr_func(x, y)
            return {
                'method': method_name,
                'correlation': round(float(corr), 4),
                'p_value': round(float(p_value), 6),
                'significant': p_value < 0.05,
                'strength': self._interpret_corr(abs(corr)),
            }
        except Exception as e:
            return {'method': method_name, 'error': str(e)}

    def pearson_analysis(self, x, y):
        return self._correlation_analysis('Pearson', stats.pearsonr, x, y)

    def spearman_analysis(self, x, y):
        return self._correlation_analysis('Spearman', stats.spearmanr, x, y)

    def covariance_analysis(self, x, y):
        try:
            cov = np.cov(x, y)
            return {
                'method': 'Covariance',
                'covariance': round(float(cov[0, 1]), 4),
                'x_variance': round(float(cov[0, 0]), 4),
                'y_variance': round(float(cov[1, 1]), 4),
                'x_cv': round(float(np.std(x) / (np.mean(x) + 1e-10)), 4),
                'y_cv': round(float(np.std(y) / (np.mean(y) + 1e-10)), 4),
            }
        except Exception as e:
            return {'method': 'Covariance', 'error': str(e)}

    def dominant_factor_analysis(self, df, target_col, feature_cols):
        try:
            results = []
            for col in feature_cols:
                if col not in df.columns or target_col not in df.columns:
                    continue
                valid = df[[col, target_col]].dropna()
                if len(valid) < 3:
                    continue
                pearson_corr, pearson_p = stats.pearsonr(valid[col], valid[target_col])
                spearman_corr, spearman_p = stats.spearmanr(valid[col], valid[target_col])
                results.append({
                    'factor': col,
                    'pearson_corr': round(float(pearson_corr), 4),
                    'pearson_p': round(float(pearson_p), 6),
                    'spearman_corr': round(float(spearman_corr), 4),
                    'spearman_p': round(float(spearman_p), 6),
                    'abs_pearson': abs(float(pearson_corr)),
                })
            results.sort(key=lambda x: x['abs_pearson'], reverse=True)
            return results
        except Exception as e:
            return {'error': str(e)}

    def partial_correlation(self, df, x_col, y_col, control_cols):
        try:
            from numpy.linalg import inv
            cols = [x_col, y_col] + control_cols
            sub = df[cols].dropna()
            if len(sub) < len(cols) + 2:
                return {'error': '数据点不足'}
            corr_matrix = np.corrcoef(sub.values, rowvar=False)
            try:
                precision = inv(corr_matrix)
            except np.linalg.LinAlgError:
                return {'error': '相关矩阵不可逆'}
            partial_corr = -precision[0, 1] / np.sqrt(
                precision[0, 0] * precision[1, 1]
            )
            return {
                'method': 'Partial Correlation',
                'partial_correlation': round(float(partial_corr), 4),
                'control_variables': control_cols,
            }
        except Exception as e:
            return {'error': str(e)}

    def _interpret_corr(self, abs_val):
        if abs_val >= 0.8:
            return '极强相关'
        elif abs_val >= 0.6:
            return '强相关'
        elif abs_val >= 0.4:
            return '中等相关'
        elif abs_val >= 0.2:
            return '弱相关'
        else:
            return '极弱相关'


growth_model = GrowthStatusModel()
carbon_model = CarbonSequestrationModel()
correlation_analyzer = EcologicalCorrelationAnalyzer()
feature_engineer = CamphorTreeFeatureEngineer()


def load_all_models():
    try:
        os.makedirs('models', exist_ok=True)
        growth_loaded = growth_model.load('models/growth_model.pkl')
        carbon_loaded = carbon_model.load('models/carbon_model.pkl')
        print(f"生长模型: {'已加载' if growth_loaded else '使用默认预测'}")
        print(f"碳汇模型: {'已加载' if carbon_loaded else '使用默认预测'}")
        return growth_loaded and carbon_loaded
    except Exception as e:
        print(f"加载模型错误: {e}")
        return False


def save_all_models():
    try:
        os.makedirs('models', exist_ok=True)
        growth_model.save('models/growth_model.pkl')
        carbon_model.save('models/carbon_model.pkl')
        return True
    except Exception as e:
        print(f"保存模型错误: {e}")
        return False


def train_with_sample_data():
    try:
        sample_data = {
            'total_precipitation': [1600, 1650, 1550, 1700, 1620, 1580, 1720, 1480],
            'avg_humidity': [75, 78, 72, 80, 76, 74, 82, 68],
            'avg_wind_speed': [2.1, 1.8, 2.3, 1.9, 2.0, 2.2, 1.7, 2.8],
            'altitude': [45, 32, 55, 28, 40, 48, 25, 60],
            'tree_height': [15, 18, 12, 20, 16, 14, 22, 10],
            'carbon_per_age': [0.57, 0.48, 0.62, 0.45, 0.55, 0.52, 0.42, 0.68],
            'growth_status': ['正常', '正常', '衰弱', '正常', '正常', '衰弱', '正常', '濒危'],
        }
        df_growth = pd.DataFrame(sample_data)
        X_growth = df_growth[growth_model.feature_columns[:6]].copy()
        y_growth = df_growth['growth_status']
        result = growth_model.train(X_growth, y_growth)
        print(f"生长模型训练完成: {result}")

        carbon_sample = {
            'tree_age': [150, 200, 100, 250, 180, 120, 220, 80],
            'dbh': [120, 150, 90, 160, 130, 100, 155, 80],
            'tree_height': [15, 18, 12, 20, 16, 13, 19, 10],
            'soil_compactness': ['中等', '疏松', '紧密', '中等', '疏松', '中等', '较疏松', '紧密'],
            'avg_humidity': [75, 78, 72, 80, 76, 74, 82, 68],
            'annual_carbon_seq': [85.5, 95.2, 65.3, 102.1, 88.7, 72.4, 98.6, 55.2],
        }
        df_carbon = pd.DataFrame(carbon_sample)
        X_carbon = df_carbon[['tree_age', 'dbh', 'tree_height', 'soil_compactness', 'avg_humidity']].copy()
        y_carbon = df_carbon['annual_carbon_seq']
        metrics = carbon_model.train(X_carbon, y_carbon)
        print(f"碳汇模型训练完成: {metrics}")

        save_all_models()
        print("模型持久化完成")
        return True
    except Exception as e:
        print(f"模型训练错误: {e}")
        return False
"""
情報技術者試験学習システム - リファクタリング版Webアプリケーション

アーキテクチャ:
- ルート層: Blueprintによる機能分割
- サービス層: ビジネスロジックの分離
- データ層: DatabaseManagerによる抽象化
"""

import os
import logging
from pathlib import Path
from flask import Flask
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
import secrets
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

# プロジェクトルートをパスに追加
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 設定とコアモジュール
from src.core.config import config
from src.core.database import DatabaseManager
from src.data.data_fetcher import IPADataFetcher, DataProcessor
from src.core.progress_tracker import ProgressTracker
from src.core.report_generator import ReportGenerator

# サービス層
from src.web.services.study_service import StudyService
from src.web.services.session_service import SessionService
from src.web.services.progress_service import ProgressService
from src.web.services.settings_service import SettingsService

# ルート層
from src.web.routes.main_routes import main_bp, init_services as init_main_services
from src.web.routes.study_routes import study_bp, init_services as init_study_services
from src.web.routes.progress_routes import progress_bp, init_services as init_progress_services
from src.web.routes.settings_routes import settings_bp, init_services as init_settings_services

class ApplicationFactory:
    """アプリケーションファクトリ"""
    
    @staticmethod
    def create_app():
        """Flaskアプリケーションを作成"""
        app = Flask(__name__, 
                   template_folder='templates',
                   static_folder='static')
        
        # 設定
        ApplicationFactory._configure_app(app)
        
        # セキュリティ
        ApplicationFactory._configure_security(app)
        
        # ログ設定
        ApplicationFactory._configure_logging(app)
        
        # サービス初期化
        services = ApplicationFactory._initialize_services()
        
        # ルート登録
        ApplicationFactory._register_blueprints(app, services)
        
        # エラーハンドラー
        ApplicationFactory._register_error_handlers(app)
        
        # テンプレートフィルター
        ApplicationFactory._register_template_filters(app)
        
        return app
    
    @staticmethod
    def _configure_app(app):
        """アプリケーション設定"""
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))
        app.config['SESSION_TYPE'] = 'filesystem'
        app.config['SESSION_PERMANENT'] = False
        app.config['SESSION_USE_SIGNER'] = True
        app.config['SESSION_FILE_DIR'] = os.environ.get(
            'SESSION_FILE_DIR', 
            str(config.PROJECT_ROOT / 'flask_session')
        )
        
        # セッション設定
        Session(app)
        
        # 静的ファイルキャッシュ設定
        if os.environ.get('FLASK_ENV') == 'production':
            app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1年
            
            @app.after_request
            def after_request(response):
                from flask import request
                if request.endpoint == 'static':
                    response.cache_control.max_age = 31536000
                    response.cache_control.public = True
                return response
    
    @staticmethod
    def _configure_security(app):
        """セキュリティ設定"""
        # CSRF保護
        CSRFProtect(app)
        
        # セキュリティヘッダー（本番環境のみ）
        if os.environ.get('FLASK_ENV') == 'production':
            csp = {
                'default-src': "'self'",
                'script-src': "'self' 'unsafe-inline'",
                'style-src': "'self' 'unsafe-inline'",
                'img-src': "'self' data:",
                'font-src': "'self'",
                'connect-src': "'self'",
                'frame-src': "'none'"
            }
            Talisman(app, 
                    force_https=True,
                    strict_transport_security=True,
                    content_security_policy=csp)
    
    @staticmethod
    def _configure_logging(app):
        """ログ設定"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(config.LOG_FILE),
                logging.StreamHandler()
            ]
        )
        app.logger.info("アプリケーション初期化完了")
    
    @staticmethod
    def _initialize_services():
        """サービス層の初期化"""
        try:
            # コアコンポーネント
            db = DatabaseManager()
            fetcher = IPADataFetcher()
            processor = DataProcessor()
            tracker = ProgressTracker(db)
            report_generator = ReportGenerator(db, tracker)
            
            # サービス層
            study_service = StudyService(db)
            session_service = SessionService(db)
            progress_service = ProgressService(db, report_generator)
            settings_service = SettingsService(db, fetcher, processor)
            
            return {
                'study': study_service,
                'session': session_service,
                'progress': progress_service,
                'settings': settings_service
            }
            
        except Exception as e:
            logging.error(f"サービス初期化エラー: {e}")
            raise
    
    @staticmethod
    def _register_blueprints(app, services):
        """Blueprintの登録"""
        # サービスの依存性注入
        init_main_services(services['study'])
        init_study_services(services['study'], services['session'])
        init_progress_services(services['progress'])
        init_settings_services(services['settings'])
        
        # Blueprint登録
        app.register_blueprint(main_bp)
        app.register_blueprint(study_bp)
        app.register_blueprint(progress_bp)
        app.register_blueprint(settings_bp)
    
    @staticmethod
    def _register_error_handlers(app):
        """エラーハンドラーの登録"""
        from flask import request, render_template
        
        @app.errorhandler(404)
        def not_found(error):
            app.logger.warning(f"404エラー: {request.url}")
            return render_template('error.html', 
                                 error_code=404, 
                                 error_message="ページが見つかりません"), 404

        @app.errorhandler(500)
        def internal_error(error):
            app.logger.error(f"500エラー: {error}")
            return render_template('error.html', 
                                 error_code=500, 
                                 error_message="内部サーバーエラーが発生しました"), 500

        @app.errorhandler(400)
        def bad_request(error):
            app.logger.warning(f"400エラー: {error}")
            return render_template('error.html',
                                 error_code=400,
                                 error_message="不正なリクエストです"), 400

        @app.errorhandler(403)
        def forbidden(error):
            app.logger.warning(f"403エラー: {error}")
            return render_template('error.html',
                                 error_code=403,
                                 error_message="アクセスが拒否されました"), 403

        @app.errorhandler(Exception)
        def handle_exception(e):
            app.logger.error(f"予期しないエラー: {e}")
            return render_template('error.html',
                                 error_code=500,
                                 error_message="予期しないエラーが発生しました"), 500
    
    @staticmethod
    def _register_template_filters(app):
        """テンプレートフィルターの登録"""
        @app.template_filter('percentage')
        def percentage_filter(value):
            if value is None:
                return "0.0%"
            return f"{value:.1f}%"

        @app.template_filter('grade_class')
        def grade_class_filter(rate):
            if rate >= 80:
                return "success"
            elif rate >= 60:
                return "info"
            elif rate >= 40:
                return "warning"
            else:
                return "danger"

        @app.template_filter('chr')
        def chr_filter(value):
            """数値を文字に変換するフィルター"""
            try:
                return chr(int(value))
            except (ValueError, TypeError):
                return str(value)

# アプリケーション作成
app = ApplicationFactory.create_app()

if __name__ == '__main__':
    # 必要なディレクトリを作成
    config.create_directories()
    
    # セッション用ディレクトリを作成
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    
    # 開発サーバーを起動
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug, host='0.0.0.0', port=port)
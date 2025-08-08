/**
 * Service Worker - PWA機能とキャッシュ管理
 */

const CACHE_NAME = 'it-exam-system-v1.0';
const STATIC_CACHE = 'static-cache-v1.0';
const DYNAMIC_CACHE = 'dynamic-cache-v1.0';

// キャッシュするリソース
const STATIC_ASSETS = [
    '/',
    '/static/styles.css',
    '/static/charts.js',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js'
];

// API エンドポイントのキャッシュ戦略
const API_CACHE_STRATEGY = {
    '/health': 'network-first',
    '/api/statistics': 'cache-first',
    '/api/questions': 'cache-first',
    '/api/progress': 'network-first'
};

// インストール時の処理
self.addEventListener('install', event => {
    console.log('Service Worker: Installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('Service Worker: Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => self.skipWaiting())
    );
});

// アクティベーション時の処理
self.addEventListener('activate', event => {
    console.log('Service Worker: Activating...');
    
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
                        console.log('Service Worker: Deleting old cache', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

// ネットワークリクエストの処理
self.addEventListener('fetch', event => {
    const request = event.request;
    const url = new URL(request.url);
    
    // Chrome拡張機能のリクエストは無視
    if (url.protocol === 'chrome-extension:') {
        return;
    }
    
    // API リクエストの処理
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(handleApiRequest(request));
        return;
    }
    
    // 静的リソースの処理
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(handleStaticRequest(request));
        return;
    }
    
    // HTML ページの処理
    if (request.headers.get('accept')?.includes('text/html')) {
        event.respondWith(handlePageRequest(request));
        return;
    }
    
    // その他のリクエストはネットワーク優先
    event.respondWith(
        fetch(request).catch(() => {
            console.warn('Service Worker: Network request failed:', request.url);
            return new Response('オフラインです', {
                status: 503,
                statusText: 'Service Unavailable'
            });
        })
    );
});

// API リクエスト処理
async function handleApiRequest(request) {
    const url = new URL(request.url);
    const strategy = getApiCacheStrategy(url.pathname);
    
    switch (strategy) {
        case 'cache-first':
            return cacheFirst(request, DYNAMIC_CACHE);
        case 'network-first':
            return networkFirst(request, DYNAMIC_CACHE);
        default:
            return fetch(request);
    }
}

// 静的リソース処理（キャッシュ優先）
async function handleStaticRequest(request) {
    return cacheFirst(request, STATIC_CACHE);
}

// HTMLページ処理（ネットワーク優先）
async function handlePageRequest(request) {
    return networkFirst(request, DYNAMIC_CACHE);
}

// キャッシュ優先戦略
async function cacheFirst(request, cacheName) {
    try {
        const cache = await caches.open(cacheName);
        const cachedResponse = await cache.match(request);
        
        if (cachedResponse) {
            console.log('Service Worker: Serving from cache:', request.url);
            // バックグラウンドでキャッシュ更新
            fetch(request).then(response => {
                if (response.ok) {
                    cache.put(request, response.clone());
                }
            }).catch(() => {}); // エラーは無視
            
            return cachedResponse;
        }
        
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
        
    } catch (error) {
        console.error('Service Worker: Cache first failed:', error);
        return fetch(request);
    }
}

// ネットワーク優先戦略
async function networkFirst(request, cacheName) {
    try {
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
        
    } catch (error) {
        console.log('Service Worker: Network failed, trying cache:', request.url);
        const cache = await caches.open(cacheName);
        const cachedResponse = await cache.match(request);
        
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // オフライン用フォールバック
        if (request.headers.get('accept')?.includes('text/html')) {
            return new Response(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>オフライン - IT試験学習システム</title>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; text-align: center; padding: 50px; }
                        .offline { color: #666; }
                        .retry-btn { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; margin-top: 20px; cursor: pointer; }
                    </style>
                </head>
                <body>
                    <h1>🔌 オフライン</h1>
                    <p class="offline">インターネット接続を確認してください。</p>
                    <p>一部の機能は引き続き利用できます。</p>
                    <button class="retry-btn" onclick="location.reload()">再試行</button>
                    <p><a href="/">ホームに戻る</a></p>
                </body>
                </html>
            `, {
                headers: { 'Content-Type': 'text/html; charset=utf-8' }
            });
        }
        
        throw error;
    }
}

// API キャッシュ戦略の決定
function getApiCacheStrategy(pathname) {
    for (const [path, strategy] of Object.entries(API_CACHE_STRATEGY)) {
        if (pathname.startsWith(path)) {
            return strategy;
        }
    }
    return 'network-only';
}

// バックグラウンド同期（対応ブラウザのみ）
self.addEventListener('sync', event => {
    console.log('Service Worker: Background sync:', event.tag);
    
    if (event.tag === 'background-sync') {
        event.waitUntil(doBackgroundSync());
    }
});

async function doBackgroundSync() {
    // 学習データの同期処理
    try {
        const pendingData = await getPendingData();
        if (pendingData.length > 0) {
            console.log('Service Worker: Syncing pending data:', pendingData.length);
            // ここで保留中のデータをサーバーに送信
            await syncPendingData(pendingData);
        }
    } catch (error) {
        console.error('Service Worker: Background sync failed:', error);
    }
}

async function getPendingData() {
    // IndexedDB からペンディングデータを取得
    return []; // 実装に応じてデータを返す
}

async function syncPendingData(data) {
    // サーバーに保留データを送信
    for (const item of data) {
        try {
            await fetch('/api/sync', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(item)
            });
        } catch (error) {
            console.error('Service Worker: Failed to sync item:', error);
        }
    }
}

// プッシュ通知処理（対応ブラウザのみ）
self.addEventListener('push', event => {
    if (!event.data) return;
    
    const data = event.data.json();
    const options = {
        body: data.body,
        icon: '/static/icon-192.png',
        badge: '/static/badge-72.png',
        vibrate: [100, 50, 100],
        data: data.data
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// 通知クリック処理
self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    const url = event.notification.data?.url || '/';
    
    event.waitUntil(
        clients.matchAll({ type: 'window' })
            .then(clientList => {
                // 既存のウィンドウがあればフォーカス
                for (const client of clientList) {
                    if (client.url === url && 'focus' in client) {
                        return client.focus();
                    }
                }
                
                // 新しいウィンドウを開く
                if (clients.openWindow) {
                    return clients.openWindow(url);
                }
            })
    );
});

// メッセージ処理（クライアントからの通信）
self.addEventListener('message', event => {
    if (event.data.action === 'cache-question-data') {
        // 問題データをキャッシュ
        const cache = caches.open(DYNAMIC_CACHE);
        cache.then(c => {
            c.put('/api/questions', new Response(JSON.stringify(event.data.questions)));
        });
    }
    
    if (event.data.action === 'clear-cache') {
        // キャッシュクリア
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => caches.delete(cacheName))
            );
        });
    }
});

console.log('Service Worker: Loaded successfully');
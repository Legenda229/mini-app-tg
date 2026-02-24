// ========================================
// JOONIX GOLD - Main Application
// ========================================

const GOLD_PRICE = 0.67;
const MIN_GOLD = 100;
const API_URL = '';  // Same origin

let tg = window.Telegram?.WebApp;
let currentUser = null;
let selectedGame = 'standoff2';
let selectedGold = 100;

// ========================================
// INITIALIZATION
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    // Init Telegram WebApp
    if (tg) {
        tg.ready();
        tg.expand();
        tg.setHeaderColor('#0a0a0f');
        tg.setBackgroundColor('#0a0a0f');
        
        // Enable haptic feedback
        if (tg.HapticFeedback) {
            tg.HapticFeedback.impactOccurred('light');
        }
    }

    // Create particles
    createParticles();

    // Generate gold cards
    generateGoldCards();

    // Load user data
    await loadUser();

    // Hide loading screen
    setTimeout(() => {
        document.getElementById('loadingScreen').classList.add('hidden');
        document.getElementById('app').style.display = 'block';
    }, 1500);
}

// ========================================
// PARTICLES
// ========================================

function createParticles() {
    const container = document.getElementById('particles');
    const count = 20;

    for (let i = 0; i < count; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 8 + 's';
        particle.style.animationDuration = (6 + Math.random() * 6) + 's';
        container.appendChild(particle);
    }
}

// ========================================
// USER
// ========================================

async function loadUser() {
    let userData = {};

    if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
        const u = tg.initDataUnsafe.user;
        userData = {
            telegram_id: u.id,
            username: u.username || '',
            first_name: u.first_name || '',
            last_name: u.last_name || '',
            photo_url: u.photo_url || ''
        };
    } else {
        // Dev mode
        userData = {
            telegram_id: 123456789,
            username: 'testuser',
            first_name: 'Test',
            last_name: 'User',
            photo_url: ''
        };
    }

    try {
        const response = await fetch(API_URL + '/api/user', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });

        const data = await response.json();
        if (data.success) {
            currentUser = data.user;
            updateUI();
        }
    } catch (e) {
        console.error('Load user error:', e);
        // Use local data
        currentUser = {
            ...userData,
            total_orders: 0,
            total_spent: 0,
            created_at: new Date().toISOString()
        };
        updateUI();
    }
}

function updateUI() {
    if (!currentUser) return;

    const name = [currentUser.first_name, currentUser.last_name].filter(Boolean).join(' ') || 'Пользователь';
    const username = currentUser.username ? `@${currentUser.username}` : '';
    const initials = (currentUser.first_name || 'U').charAt(0).toUpperCase();

    // Avatar
    const avatarElements = document.querySelectorAll('#userAvatar, #profileAvatar');
    avatarElements.forEach(el => {
        if (currentUser.photo_url) {
            el.src = currentUser.photo_url;
        } else {
            el.style.display = 'none';
            el.parentElement.style.background = 'linear-gradient(135deg, var(--accent), var(--accent-dark))';
            el.parentElement.style.display = 'flex';
            el.parentElement.style.alignItems = 'center';
            el.parentElement.style.justifyContent = 'center';
            el.parentElement.style.fontSize = el.parentElement.classList.contains('profile-avatar-large') ? '36px' : '16px';
            el.parentElement.style.fontWeight = '800';
            el.parentElement.style.color = 'white';
            if (!el.parentElement.querySelector('.avatar-initial')) {
                const span = document.createElement('span');
                span.className = 'avatar-initial';
                span.textContent = initials;
                el.parentElement.appendChild(span);
            }
        }
    });

    // Profile info
    document.getElementById('profileName').textContent = name;
    document.getElementById('profileUsername').textContent = username || 'Нет username';
    document.getElementById('profileId').textContent = `ID: ${currentUser.telegram_id}`;

    // Stats
    document.getElementById('statOrders').textContent = currentUser.total_orders || 0;
    document.getElementById('statSpent').textContent = `${(currentUser.total_spent || 0).toFixed(0)}₽`;

    if (currentUser.created_at) {
        const date = new Date(currentUser.created_at);
        document.getElementById('statDate').textContent = date.toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'short'
        });
    }
}

// ========================================
// GOLD CARDS
// ========================================

function generateGoldCards() {
    const grid = document.querySelector('.quick-buy-grid');
    const amounts = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000];

    grid.innerHTML = amounts.map((amount, i) => {
        const price = (amount * GOLD_PRICE).toFixed(2);
        const isPopular = amount === 500;
        
        return `
            <div class="gold-card ${isPopular ? 'popular' : ''}" 
                 onclick="quickBuy(${amount})" 
                 style="animation-delay: ${i * 0.05}s">
                <div class="gold-card-shimmer"></div>
                ${isPopular ? '<div class="popular-tag">Популярное</div>' : ''}
                <div class="gold-amount">
                    <i class="fas fa-coins"></i>
                    <span>${amount}</span>
                </div>
                <div class="gold-label">голды</div>
                <div class="gold-price">${price}₽</div>
                <div class="gold-price-sub">${GOLD_PRICE}₽/шт</div>
            </div>
        `;
    }).join('');
}

// ========================================
// GAME SELECTION
// ========================================

function selectGame(game) {
    if (game === 'brawlstars') {
        showToast('Brawl Stars скоро будет доступен!', 'info');
        haptic('warning');
        return;
    }

    selectedGame = game;
    haptic('light');

    document.querySelectorAll('.category-card').forEach(card => {
        card.classList.toggle('active', card.dataset.game === game);
    });
}

// ========================================
// AMOUNT CONTROLS
// ========================================

function changeAmount(delta) {
    const input = document.getElementById('customAmount');
    let value = parseInt(input.value) || MIN_GOLD;
    value = Math.max(MIN_GOLD, value + delta);
    value = Math.min(10000, value);
    input.value = value;
    document.getElementById('amountSlider').value = value;
    updateCustomPrice();
    haptic('light');
}

function updateFromSlider() {
    const slider = document.getElementById('amountSlider');
    const input = document.getElementById('customAmount');
    input.value = slider.value;
    updateCustomPrice();
}

function updateCustomPrice() {
    const input = document.getElementById('customAmount');
    let amount = parseInt(input.value) || MIN_GOLD;
    amount = Math.max(MIN_GOLD, amount);
    
    const price = (amount * GOLD_PRICE).toFixed(2);
    
    document.getElementById('displayGold').textContent = amount.toLocaleString();
    document.getElementById('displayPrice').textContent = `${price}₽`;
    selectedGold = amount;

    // Sync slider
    document.getElementById('amountSlider').value = Math.min(amount, 10000);
}

// ========================================
// PURCHASE
// ========================================

function quickBuy(amount) {
    selectedGold = amount;
    document.getElementById('customAmount').value = amount;
    document.getElementById('amountSlider').value = amount;
    updateCustomPrice();
    openBuyModal();
    haptic('medium');
}

function openBuyModal() {
    const price = (selectedGold * GOLD_PRICE).toFixed(2);
    
    document.getElementById('modalGold').textContent = selectedGold.toLocaleString();
    document.getElementById('modalPrice').textContent = `${price}₽`;
    document.getElementById('gameIdInput').value = '';
    
    document.getElementById('buyModal').classList.add('active');
    haptic('light');
}

function closeBuyModal() {
    document.getElementById('buyModal').classList.remove('active');
    haptic('light');
}

async function confirmOrder() {
    const gameId = document.getElementById('gameIdInput').value.trim();
    
    if (!gameId) {
        showToast('Введите ваш игровой ID!', 'error');
        haptic('error');
        return;
    }

    if (selectedGold < MIN_GOLD) {
        showToast(`Минимум ${MIN_GOLD} голды!`, 'error');
        haptic('error');
        return;
    }

    try {
        const response = await fetch(API_URL + '/api/order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: currentUser?.telegram_id || 0,
                game: selectedGame,
                gold_amount: selectedGold,
                game_id: gameId
            })
        });

        const data = await response.json();

        if (data.success) {
            closeBuyModal();
            
            // Show success
            document.getElementById('successOrderId').textContent = data.order.id;
            setTimeout(() => {
                document.getElementById('successModal').classList.add('active');
                haptic('success');
            }, 300);

            // Send data to Telegram
            if (tg) {
                tg.sendData(JSON.stringify({
                    order_id: data.order.id,
                    game: selectedGame,
                    gold_amount: selectedGold,
                    price: data.order.price,
                    game_id: gameId
                }));
            }

            // Update user stats
            if (currentUser) {
                currentUser.total_orders = (currentUser.total_orders || 0) + 1;
                currentUser.total_spent = (currentUser.total_spent || 0) + data.order.price;
                updateUI();
            }

            // Refresh orders
            loadOrders();
        } else {
            showToast(data.error || 'Ошибка создания заказа', 'error');
            haptic('error');
        }
    } catch (e) {
        console.error('Order error:', e);
        showToast('Ошибка соединения', 'error');
        haptic('error');
    }
}

function closeSuccessModal() {
    document.getElementById('successModal').classList.remove('active');
}

// ========================================
// ORDERS
// ========================================

async function loadOrders() {
    if (!currentUser) return;

    try {
        const response = await fetch(API_URL + '/api/orders', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ telegram_id: currentUser.telegram_id })
        });

        const data = await response.json();

        if (data.success && data.orders.length > 0) {
            renderOrders(data.orders);
        }
    } catch (e) {
        console.error('Load orders error:', e);
    }
}

function renderOrders(orders) {
    const container = document.getElementById('ordersList');
    
    const statusMap = {
        pending: { icon: 'fas fa-clock', class: 'pending', text: 'В обработке' },
        completed: { icon: 'fas fa-check', class: 'completed', text: 'Выполнен' },
        cancelled: { icon: 'fas fa-times', class: 'cancelled', text: 'Отменён' }
    };

    const gameMap = {
        standoff2: 'Standoff 2',
        brawlstars: 'Brawl Stars'
    };

    container.innerHTML = orders.map(order => {
        const status = statusMap[order.status] || statusMap.pending;
        const gameName = gameMap[order.game] || order.game;
        const date = new Date(order.created_at).toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit'
        });

        return `
            <div class="order-item">
                <div class="order-icon ${status.class}">
                    <i class="${status.icon}"></i>
                </div>
                <div class="order-info">
                    <h4>${gameName} — ${order.gold_amount} голды</h4>
                    <p>Заказ #${order.id} • ${date}</p>
                </div>
                <div class="order-price">
                    <div class="amount">${order.price.toFixed(2)}₽</div>
                    <div class="status status-${order.status}">${status.text}</div>
                </div>
            </div>
        `;
    }).join('');
}

// ========================================
// NAVIGATION
// ========================================

function switchPage(page) {
    // Update tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.page === page);
    });

    // Update pages
    document.querySelectorAll('.page').forEach(p => {
        p.classList.remove('active');
    });
    document.getElementById(`page-${page}`).classList.add('active');

    // Load data if needed
    if (page === 'orders') {
        loadOrders();
    }

    haptic('light');
}

function showProfile() {
    switchPage('profile');
}

// ========================================
// TOAST NOTIFICATIONS
// ========================================

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const icon = toast.querySelector('.toast-icon');
    const text = toast.querySelector('.toast-text');

    toast.className = 'toast';
    
    switch (type) {
        case 'error':
            toast.classList.add('error');
            icon.className = 'toast-icon fas fa-exclamation-circle';
            break;
        case 'success':
            toast.classList.add('success');
            icon.className = 'toast-icon fas fa-check-circle';
            break;
        default:
            icon.className = 'toast-icon fas fa-info-circle';
    }

    text.textContent = message;
    toast.classList.add('show');

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// ========================================
// HAPTIC FEEDBACK
// ========================================

function haptic(type = 'light') {
    if (tg && tg.HapticFeedback) {
        switch (type) {
            case 'light':
                tg.HapticFeedback.impactOccurred('light');
                break;
            case 'medium':
                tg.HapticFeedback.impactOccurred('medium');
                break;
            case 'heavy':
                tg.HapticFeedback.impactOccurred('heavy');
                break;
            case 'success':
                tg.HapticFeedback.notificationOccurred('success');
                break;
            case 'warning':
                tg.HapticFeedback.notificationOccurred('warning');
                break;
            case 'error':
                tg.HapticFeedback.notificationOccurred('error');
                break;
        }
    }
                  }

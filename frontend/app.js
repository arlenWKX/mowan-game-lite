const { createApp, ref, computed, onMounted, onUnmounted, watch } = Vue;
const { createRouter, createWebHashHistory, useRoute, useRouter } = VueRouter;

// ===== API Service =====
const API_BASE = localStorage.getItem('serverUrl') || '';

const api = axios.create({
    baseURL: API_BASE + '/api',
    timeout: 10000
});

api.interceptors.request.use(config => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

api.interceptors.response.use(
    response => response,
    error => {
        if (error.response?.status === 401) {
            localStorage.removeItem('token');
            router.push('/login');
        }
        return Promise.reject(error);
    }
);

// ===== Toast Service =====
const toasts = ref([]);

const showToast = (message, type = 'info') => {
    const id = Date.now();
    toasts.value.push({ id, message, type });
    setTimeout(() => {
        toasts.value = toasts.value.filter(t => t.id !== id);
    }, 3000);
};

// ===== Components =====

// Toast Container
const ToastContainer = {
    setup() {
        return { toasts };
    },
    template: `
        <div class="toast-container">
            <div v-for="toast in toasts" :key="toast.id" :class="['toast', toast.type]">
                {{ toast.message }}
            </div>
        </div>
    `
};

// Header Component
const AppHeader = {
    setup() {
        const router = useRouter();
        const isLoggedIn = computed(() => !!localStorage.getItem('token'));
        const user = ref(null);
        
        const loadUser = async () => {
            if (isLoggedIn.value) {
                try {
                    const res = await api.get('/auth/me');
                    user.value = res.data;
                } catch (e) {
                    console.error(e);
                }
            }
        };
        
        const logout = () => {
            localStorage.removeItem('token');
            user.value = null;
            router.push('/');
            showToast('已退出登录', 'info');
        };
        
        onMounted(loadUser);
        
        return { isLoggedIn, user, logout };
    },
    template: `
        <header class="header">
            <router-link to="/" class="logo">魔丸小游戏</router-link>
            <nav class="nav-links">
                <router-link to="/">首页</router-link>
                <router-link to="/leaderboard">排行榜</router-link>
                <router-link to="/rules">规则</router-link>
                <template v-if="isLoggedIn">
                    <router-link to="/rooms">房间</router-link>
                    <router-link v-if="user?.is_admin" to="/admin">管理</router-link>
                    <div class="user-info">
                        <span>{{ user?.nickname }}</span>
                        <button @click="logout" class="btn btn-sm btn-secondary">退出</button>
                    </div>
                </template>
                <template v-else>
                    <router-link to="/login">登录</router-link>
                    <router-link to="/register">注册</router-link>
                </template>
            </nav>
        </header>
    `
};

// Home Page
const HomePage = {
    setup() {
        const router = useRouter();
        const isLoggedIn = computed(() => !!localStorage.getItem('token'));
        const serverUrl = ref(localStorage.getItem('serverUrl') || '');
        
        const saveServerUrl = () => {
            localStorage.setItem('serverUrl', serverUrl.value);
            showToast('服务器地址已保存', 'success');
            location.reload();
        };
        
        const offlineMode = () => {
            showToast('进入离线模式', 'info');
            router.push('/offline');
        };
        
        return { isLoggedIn, serverUrl, saveServerUrl, offlineMode };
    },
    template: `
        <div class="container">
            <div class="card text-center" style="padding: 60px 20px;">
                <h1 style="font-size: 3rem; margin-bottom: 20px;">
                    <span style="background: linear-gradient(135deg, #6366f1, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                        魔丸小游戏
                    </span>
                </h1>
                <p class="text-muted" style="font-size: 1.25rem; margin-bottom: 40px;">
                    策略推理 · 数字对决 · 智谋较量
                </p>
                <div class="flex gap-4 justify-center" style="flex-wrap: wrap;">
                    <router-link v-if="isLoggedIn" to="/rooms" class="btn btn-primary" style="font-size: 1.125rem; padding: 16px 32px;">
                        开始游戏
                    </router-link>
                    <router-link v-else to="/login" class="btn btn-primary" style="font-size: 1.125rem; padding: 16px 32px;">
                        登录 / 注册
                    </router-link>
                    <button @click="offlineMode" class="btn btn-secondary" style="font-size: 1.125rem; padding: 16px 32px;">
                        离线模式
                    </button>
                </div>
            </div>
            
            <div class="card">
                <h3 class="card-title">服务器设置</h3>
                <div class="form-group">
                    <label class="form-label">服务器地址</label>
                    <div class="flex gap-4">
                        <input v-model="serverUrl" class="form-input" placeholder="http://localhost:5000">
                        <button @click="saveServerUrl" class="btn btn-primary">保存</button>
                    </div>
                    <p class="text-muted mt-4">留空表示使用当前域名</p>
                </div>
            </div>
            
            <div class="grid grid-3">
                <div class="card text-center">
                    <div style="font-size: 3rem; margin-bottom: 16px;">🎮</div>
                    <h3>策略对战</h3>
                    <p class="text-muted">2-5人实时对战，考验你的策略思维</p>
                </div>
                <div class="card text-center">
                    <div style="font-size: 3rem; margin-bottom: 16px;">🧩</div>
                    <h3>独特规则</h3>
                    <p class="text-muted">反向排序对决，特殊数字克制关系</p>
                </div>
                <div class="card text-center">
                    <div style="font-size: 3rem; margin-bottom: 16px;">🏆</div>
                    <h3>排行榜</h3>
                    <p class="text-muted">与全球玩家一较高下</p>
                </div>
            </div>
        </div>
    `
};

// Login Page
const LoginPage = {
    setup() {
        const router = useRouter();
        const username = ref('');
        const password = ref('');
        const loading = ref(false);
        
        const login = async () => {
            if (!username.value || !password.value) {
                showToast('请填写用户名和密码', 'error');
                return;
            }
            loading.value = true;
            try {
                const res = await api.post('/auth/login', {
                    username: username.value,
                    password: password.value
                });
                localStorage.setItem('token', res.data.access_token);
                showToast('登录成功', 'success');
                router.push('/rooms');
            } catch (e) {
                showToast(e.response?.data?.error || '登录失败', 'error');
            } finally {
                loading.value = false;
            }
        };
        
        return { username, password, loading, login };
    },
    template: `
        <div class="container" style="max-width: 400px; padding-top: 60px;">
            <div class="card">
                <h2 class="card-title text-center">登录</h2>
                <div class="form-group">
                    <label class="form-label">用户名</label>
                    <input v-model="username" class="form-input" placeholder="请输入用户名">
                </div>
                <div class="form-group">
                    <label class="form-label">密码</label>
                    <input v-model="password" type="password" class="form-input" placeholder="请输入密码">
                </div>
                <button @click="login" :disabled="loading" class="btn btn-primary w-full">
                    {{ loading ? '登录中...' : '登录' }}
                </button>
                <p class="text-center mt-4 text-muted">
                    还没有账号？<router-link to="/register" style="color: var(--primary);">立即注册</router-link>
                </p>
            </div>
        </div>
    `
};

// Register Page
const RegisterPage = {
    setup() {
        const router = useRouter();
        const username = ref('');
        const password = ref('');
        const nickname = ref('');
        const loading = ref(false);
        
        const register = async () => {
            if (!username.value || !password.value || !nickname.value) {
                showToast('请填写所有字段', 'error');
                return;
            }
            if (password.value.length < 6) {
                showToast('密码至少6位', 'error');
                return;
            }
            loading.value = true;
            try {
                await api.post('/auth/register', {
                    username: username.value,
                    password: password.value,
                    nickname: nickname.value
                });
                showToast('注册成功，请登录', 'success');
                router.push('/login');
            } catch (e) {
                showToast(e.response?.data?.error || '注册失败', 'error');
            } finally {
                loading.value = false;
            }
        };
        
        return { username, password, nickname, loading, register };
    },
    template: `
        <div class="container" style="max-width: 400px; padding-top: 60px;">
            <div class="card">
                <h2 class="card-title text-center">注册</h2>
                <div class="form-group">
                    <label class="form-label">用户名</label>
                    <input v-model="username" class="form-input" placeholder="至少3个字符">
                </div>
                <div class="form-group">
                    <label class="form-label">昵称</label>
                    <input v-model="nickname" class="form-input" placeholder="显示名称">
                </div>
                <div class="form-group">
                    <label class="form-label">密码</label>
                    <input v-model="password" type="password" class="form-input" placeholder="至少6位">
                </div>
                <button @click="register" :disabled="loading" class="btn btn-primary w-full">
                    {{ loading ? '注册中...' : '注册' }}
                </button>
                <p class="text-center mt-4 text-muted">
                    已有账号？<router-link to="/login" style="color: var(--primary);">立即登录</router-link>
                </p>
            </div>
        </div>
    `
};

// Rooms Page
const RoomsPage = {
    setup() {
        const router = useRouter();
        const rooms = ref([]);
        const showCreateModal = ref(false);
        const maxPlayers = ref(2);
        const loading = ref(false);
        const joinRoomId = ref('');
        
        const createRoom = async () => {
            loading.value = true;
            try {
                const res = await api.post('/rooms', { max_players: maxPlayers.value });
                showToast('房间创建成功', 'success');
                router.push('/room/' + res.data.room_id);
            } catch (e) {
                showToast(e.response?.data?.error || '创建失败', 'error');
            } finally {
                loading.value = false;
                showCreateModal.value = false;
            }
        };
        
        const joinRoom = async () => {
            if (!joinRoomId.value) {
                showToast('请输入房间ID', 'error');
                return;
            }
            try {
                await api.post('/rooms/' + joinRoomId.value + '/join');
                router.push('/room/' + joinRoomId.value);
            } catch (e) {
                showToast(e.response?.data?.error || '加入失败', 'error');
            }
        };
        
        return { 
            rooms, showCreateModal, maxPlayers, loading, joinRoomId,
            createRoom, joinRoom 
        };
    },
    template: `
        <div class="container">
            <div class="flex justify-between items-center mb-4">
                <h2>游戏房间</h2>
                <button @click="showCreateModal = true" class="btn btn-primary">创建房间</button>
            </div>
            
            <div class="card">
                <h3 class="card-title">加入房间</h3>
                <div class="flex gap-4">
                    <input v-model="joinRoomId" class="form-input" placeholder="输入4位房间ID">
                    <button @click="joinRoom" class="btn btn-primary">加入</button>
                </div>
            </div>
            
            <!-- Create Room Modal -->
            <div v-if="showCreateModal" class="modal-overlay" @click="showCreateModal = false">
                <div class="modal-content" @click.stop>
                    <div class="modal-header">
                        <h3 class="modal-title">创建房间</h3>
                        <button @click="showCreateModal = false" class="modal-close">&times;</button>
                    </div>
                    <div class="form-group">
                        <label class="form-label">玩家人数</label>
                        <select v-model="maxPlayers" class="form-input">
                            <option :value="2">2人</option>
                            <option :value="3">3人</option>
                            <option :value="4">4人</option>
                            <option :value="5">5人</option>
                        </select>
                    </div>
                    <button @click="createRoom" :disabled="loading" class="btn btn-primary w-full">
                        {{ loading ? '创建中...' : '创建' }}
                    </button>
                </div>
            </div>
        </div>
    `
};

// Room Detail Page
const RoomPage = {
    setup() {
        const route = useRoute();
        const router = useRouter();
        const roomId = route.params.id;
        const room = ref(null);
        const players = ref([]);
        const gameState = ref(null);
        const currentUser = ref(null);
        
        // Deployment phase
        const myBoard = ref({});
        const selectedNumber = ref(null);
        const isDeployed = ref(false);
        
        // Game phase
        const selectedCell = ref(null);
        
        let pollInterval = null;
        
        const initBoard = () => {
            const board = {};
            for (let row = 1; row <= 3; row++) {
                for (let col of ['A', 'B', 'C', 'D', 'E', 'F']) {
                    board[`${row}${col}`] = null;
                }
            }
            myBoard.value = board;
        };
        
        const loadRoom = async () => {
            try {
                const res = await api.get('/rooms/' + roomId);
                room.value = res.data.room;
                players.value = res.data.players;
            } catch (e) {
                showToast('房间不存在', 'error');
                router.push('/rooms');
            }
        };
        
        const loadGameState = async () => {
            try {
                const res = await api.get('/rooms/' + roomId + '/state');
                gameState.value = res.data;
            } catch (e) {
                console.error(e);
            }
        };
        
        const loadUser = async () => {
            try {
                const res = await api.get('/auth/me');
                currentUser.value = res.data;
            } catch (e) {
                console.error(e);
            }
        };
        
        const selectNumber = (num) => {
            if (isDeployed.value) return;
            selectedNumber.value = num;
        };
        
        const placeNumber = (cellId) => {
            if (isDeployed.value || selectedNumber.value === null) return;
            if (myBoard.value[cellId] !== null) return;
            
            myBoard.value[cellId] = selectedNumber.value;
            selectedNumber.value = null;
        };
        
        const clearCell = (cellId) => {
            if (isDeployed.value) return;
            myBoard.value[cellId] = null;
        };
        
        const getAvailableNumbers = () => {
            const used = new Set();
            for (let cellId in myBoard.value) {
                if (myBoard.value[cellId] !== null) {
                    used.add(myBoard.value[cellId]);
                }
            }
            return Array.from({length: 10}, (_, i) => i).filter(n => !used.has(n));
        };
        
        const deployedCount = computed(() => {
            return Object.values(myBoard.value).filter(v => v !== null).length;
        });
        
        const submitDeployment = async () => {
            if (deployedCount.value !== 10) {
                showToast('请放置所有10个数字', 'error');
                return;
            }
            try {
                await api.post('/rooms/' + roomId + '/ready', { board: myBoard.value });
                isDeployed.value = true;
                showToast('部署完成', 'success');
            } catch (e) {
                showToast(e.response?.data?.error || '部署失败', 'error');
            }
        };
        
        const startGame = async () => {
            try {
                await api.post('/rooms/' + roomId + '/start');
                showToast('游戏开始', 'success');
                loadRoom();
            } catch (e) {
                showToast(e.response?.data?.error || '开始失败', 'error');
            }
        };
        
        const leaveRoom = async () => {
            try {
                await api.post('/rooms/' + roomId + '/leave');
                router.push('/rooms');
            } catch (e) {
                showToast('离开失败', 'error');
            }
        };
        
        const kickPlayer = async (playerId) => {
            try {
                await api.post('/rooms/' + roomId + '/kick/' + playerId);
                showToast('已踢出玩家', 'success');
                loadRoom();
            } catch (e) {
                showToast('踢出失败', 'error');
            }
        };
        
        const isCreator = computed(() => {
            return room.value && currentUser.value && room.value.creator_id === currentUser.value.id;
        });
        
        const isMyTurn = computed(() => {
            return gameState.value && gameState.value.your_turn;
        });
        
        const canStart = computed(() => {
            return isCreator.value && room.value?.status === 'waiting' && players.value.length >= 2;
        });
        
        const doAction = async (actionType, actionData = {}) => {
            try {
                await api.post('/rooms/' + roomId + '/action', {
                    action_type: actionType,
                    action_data: actionData
                });
                showToast('行动已执行', 'success');
                loadGameState();
            } catch (e) {
                showToast(e.response?.data?.error || '行动失败', 'error');
            }
        };
        
        const moveForward = (cellId) => {
            doAction('forward', { cell_id: cellId });
        };
        
        const passTurn = () => {
            doAction('pass');
        };
        
        onMounted(() => {
            initBoard();
            loadRoom();
            loadUser();
            pollInterval = setInterval(() => {
                loadRoom();
                if (room.value?.status === 'playing') {
                    loadGameState();
                }
            }, 2000);
        });
        
        onUnmounted(() => {
            if (pollInterval) clearInterval(pollInterval);
        });
        
        return {
            room, players, gameState, currentUser, myBoard, selectedNumber,
            isDeployed, deployedCount, isCreator, isMyTurn, canStart,
            selectNumber, placeNumber, clearCell, getAvailableNumbers,
            submitDeployment, startGame, leaveRoom, kickPlayer,
            moveForward, passTurn
        };
    },
    template: `
        <div class="container">
            <div v-if="!room" class="loading">
                <div class="spinner"></div>
            </div>
            <template v-else>
                <div class="flex justify-between items-center mb-4">
                    <div>
                        <h2>房间 {{ room.id }}</h2>
                        <p class="text-muted">状态: {{ room.status === 'waiting' ? '等待中' : room.status === 'playing' ? '游戏中' : '已结束' }}</p>
                    </div>
                    <button @click="leaveRoom" class="btn btn-secondary">离开房间</button>
                </div>
                
                <!-- Player List -->
                <div class="card">
                    <h3 class="card-title">玩家 ({{ players.length }}/{{ room.max_players }})</h3>
                    <div class="player-list">
                        <div v-for="player in players" :key="player.user_id" class="player-item">
                            <div class="player-avatar">{{ player.nickname[0] }}</div>
                            <div class="player-info">
                                <div class="player-name">{{ player.nickname }}</div>
                                <div class="player-status">
                                    {{ player.user_id === room.creator_id ? '房主' : '' }}
                                    {{ player.is_ready ? '已准备' : '' }}
                                </div>
                            </div>
                            <button v-if="isCreator && player.user_id !== currentUser?.id && room.status === 'waiting'"
                                    @click="kickPlayer(player.user_id)" class="btn btn-sm btn-danger">
                                踢出
                            </button>
                        </div>
                    </div>
                    <button v-if="canStart" @click="startGame" class="btn btn-success w-full mt-4">
                        开始游戏
                    </button>
                </div>
                
                <!-- Deployment Phase -->
                <div v-if="room.status === 'waiting'" class="card">
                    <h3 class="card-title">部署阶段 - 放置你的数字 ({{ deployedCount }}/10)</h3>
                    <p class="text-muted mb-4">选择数字后点击格子放置</p>
                    
                    <div class="game-board">
                        <div v-for="(num, cellId) in myBoard" :key="cellId"
                             :class="['board-cell', { occupied: num !== null }]"
                             @click="num === null ? placeNumber(cellId) : clearCell(cellId)">
                            {{ num !== null ? num : '' }}
                        </div>
                    </div>
                    
                    <div class="number-palette">
                        <button v-for="num in getAvailableNumbers()" :key="num"
                                :class="['number-btn', { selected: selectedNumber === num }]"
                                @click="selectNumber(num)">
                            {{ num }}
                        </button>
                    </div>
                    
                    <button v-if="!isDeployed" @click="submitDeployment" 
                            :disabled="deployedCount !== 10" class="btn btn-primary w-full mt-4">
                        确认部署
                    </button>
                    <p v-else class="text-center text-success mt-4">已部署完成，等待游戏开始</p>
                </div>
                
                <!-- Game Phase -->
                <div v-if="room.status === 'playing' && gameState" class="card">
                    <h3 class="card-title">
                        第 {{ gameState.current_round }} 回合
                        <span v-if="isMyTurn" class="pulse" style="color: var(--success);">你的回合!</span>
                    </h3>
                    
                    <!-- Public Area -->
                    <div class="mb-4">
                        <h4 class="text-muted mb-2">公共区域</h4>
                        <div class="public-area">
                            <div v-for="(piece, idx) in gameState.public_area" :key="idx" class="public-piece">
                                {{ piece.number }}
                            </div>
                            <p v-if="gameState.public_area.length === 0" class="text-muted">空</p>
                        </div>
                    </div>
                    
                    <!-- Player Boards -->
                    <div v-for="(data, playerId) in gameState.player_boards" :key="playerId" class="mb-4">
                        <h4 class="text-muted mb-2">{{ data.nickname }} 的棋盘</h4>
                        <div class="game-board" style="max-width: 300px;">
                            <div v-for="(val, cellId) in data.board" :key="cellId"
                                 :class="['board-cell', { occupied: val !== null }]"
                                 style="font-size: 1rem;">
                                {{ val === 'occupied' ? '●' : val !== null ? val : '' }}
                            </div>
                        </div>
                        <div v-if="data.eliminated.length > 0" class="mt-2">
                            <span class="text-muted">已淘汰: </span>
                            <span v-for="n in data.eliminated" :key="n" class="number-btn used" style="width: 32px; height: 32px; font-size: 0.875rem;">
                                {{ n }}
                            </span>
                        </div>
                    </div>
                    
                    <!-- Actions -->
                    <div v-if="isMyTurn" class="flex gap-4 justify-center mt-4">
                        <button @click="passTurn" class="btn btn-secondary">放弃行动</button>
                    </div>
                </div>
            </template>
        </div>
    `
};

// Leaderboard Page
const LeaderboardPage = {
    setup() {
        const users = ref([]);
        const loading = ref(false);
        
        const loadLeaderboard = async () => {
            loading.value = true;
            try {
                const res = await api.get('/leaderboard');
                users.value = res.data;
            } catch (e) {
                showToast('加载失败', 'error');
            } finally {
                loading.value = false;
            }
        };
        
        onMounted(loadLeaderboard);
        
        return { users, loading };
    },
    template: `
        <div class="container">
            <h2 class="mb-4">排行榜</h2>
            <div class="card">
                <div v-if="loading" class="loading">
                    <div class="spinner"></div>
                </div>
                <table v-else class="leaderboard-table">
                    <thead>
                        <tr>
                            <th>排名</th>
                            <th>玩家</th>
                            <th>胜场</th>
                            <th>败场</th>
                            <th>总场次</th>
                            <th>胜率</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(user, idx) in users" :key="idx">
                            <td :class="['rank-' + (idx + 1)]">{{ idx + 1 }}</td>
                            <td>{{ user.nickname }}</td>
                            <td>{{ user.wins }}</td>
                            <td>{{ user.losses }}</td>
                            <td>{{ user.total_games }}</td>
                            <td>{{ user.win_rate }}%</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    `
};

// Rules Page
const RulesPage = {
    template: `
        <div class="container">
            <h2 class="mb-4">游戏规则</h2>
            <div class="card rules-section">
                <h3>【游戏概览】</h3>
                <ul>
                    <li><strong>游戏类型：</strong>策略推理类棋类游戏</li>
                    <li><strong>玩家人数：</strong>2-5人</li>
                    <li><strong>游戏时长：</strong>20-40分钟</li>
                </ul>
                
                <h3>【游戏配件】</h3>
                <ul>
                    <li><strong>玩家棋盘：</strong>3行×6列网格，坐标格式为[行号][列号]，如1A、2B、3F</li>
                    <li><strong>数字棋子：</strong>每位玩家拥有0-9共10枚数字棋子</li>
                    <li><strong>公共区域：</strong>桌面中央共享结算区</li>
                    <li><strong>淘汰区：</strong>每位玩家独立的淘汰记录</li>
                </ul>
                
                <h3>【游戏流程】</h3>
                <p><strong>阶段一：部署</strong></p>
                <ul>
                    <li>每位玩家将数字0-9填入个人棋盘的任意10个不同格子中</li>
                </ul>
                
                <p><strong>阶段二：行动</strong></p>
                <ul>
                    <li><strong>前进：</strong>将棋子向前移动一格，前排棋子进入公共区域</li>
                    <li><strong>单挑：</strong>强制将其他玩家的棋子移入公共区域（额外行动）</li>
                    <li><strong>回收：</strong>将公共区域中的己方棋子回收重新部署（额外行动）</li>
                </ul>
                
                <h3>【对决规则】</h3>
                <p><strong>特殊规则（优先级最高）：</strong></p>
                <ul>
                    <li>相同数字同归于尽</li>
                    <li>0与6/9同归于尽</li>
                    <li>8 > 0</li>
                </ul>
                
                <p><strong>一般规则（反向排序）：</strong></p>
                <ul>
                    <li>0 > 1 > 2 > 3 > 4 > 5 > 6 > 7 > 8 > 9</li>
                    <li>较小数字获胜！</li>
                </ul>
                
                <h3>【胜利条件】</h3>
                <p>当某一轮完成后，场上仅剩一位玩家拥有未被击败的数字，该玩家获胜。</p>
            </div>
        </div>
    `
};

// Admin Page
const AdminPage = {
    setup() {
        const users = ref([]);
        const loading = ref(false);
        
        const loadUsers = async () => {
            loading.value = true;
            try {
                const res = await api.get('/admin/users');
                users.value = res.data;
            } catch (e) {
                showToast('加载失败', 'error');
            } finally {
                loading.value = false;
            }
        };
        
        const banUser = async (userId) => {
            try {
                await api.post('/admin/users/' + userId + '/ban');
                showToast('已封禁', 'success');
                loadUsers();
            } catch (e) {
                showToast('操作失败', 'error');
            }
        };
        
        const unbanUser = async (userId) => {
            try {
                await api.post('/admin/users/' + userId + '/unban');
                showToast('已解封', 'success');
                loadUsers();
            } catch (e) {
                showToast('操作失败', 'error');
            }
        };
        
        const deleteUser = async (userId) => {
            if (!confirm('确定删除此用户？')) return;
            try {
                await api.delete('/admin/users/' + userId);
                showToast('已删除', 'success');
                loadUsers();
            } catch (e) {
                showToast('删除失败', 'error');
            }
        };
        
        onMounted(loadUsers);
        
        return { users, loading, banUser, unbanUser, deleteUser };
    },
    template: `
        <div class="container">
            <h2 class="mb-4">用户管理</h2>
            <div class="card">
                <div v-if="loading" class="loading">
                    <div class="spinner"></div>
                </div>
                <table v-else class="leaderboard-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>用户名</th>
                            <th>昵称</th>
                            <th>管理员</th>
                            <th>状态</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="user in users" :key="user.id">
                            <td>{{ user.id }}</td>
                            <td>{{ user.username }}</td>
                            <td>{{ user.nickname }}</td>
                            <td>{{ user.is_admin ? '是' : '否' }}</td>
                            <td>{{ user.is_banned ? '已封禁' : '正常' }}</td>
                            <td>
                                <button v-if="!user.is_banned && !user.is_admin" 
                                        @click="banUser(user.id)" class="btn btn-sm btn-danger">封禁</button>
                                <button v-if="user.is_banned" 
                                        @click="unbanUser(user.id)" class="btn btn-sm btn-success">解封</button>
                                <button v-if="!user.is_admin" 
                                        @click="deleteUser(user.id)" class="btn btn-sm btn-danger">删除</button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    `
};

// Offline Mode Page
const OfflinePage = {
    setup() {
        const myBoard = ref({});
        const selectedNumber = ref(null);
        const showTutorial = ref(true);
        
        const initBoard = () => {
            const board = {};
            for (let row = 1; row <= 3; row++) {
                for (let col of ['A', 'B', 'C', 'D', 'E', 'F']) {
                    board[`${row}${col}`] = null;
                }
            }
            myBoard.value = board;
        };
        
        const selectNumber = (num) => {
            selectedNumber.value = num;
        };
        
        const placeNumber = (cellId) => {
            if (selectedNumber.value === null) return;
            if (myBoard.value[cellId] !== null) return;
            myBoard.value[cellId] = selectedNumber.value;
            selectedNumber.value = null;
        };
        
        const clearCell = (cellId) => {
            myBoard.value[cellId] = null;
        };
        
        const getAvailableNumbers = () => {
            const used = new Set();
            for (let cellId in myBoard.value) {
                if (myBoard.value[cellId] !== null) {
                    used.add(myBoard.value[cellId]);
                }
            }
            return Array.from({length: 10}, (_, i) => i).filter(n => !used.has(n));
        };
        
        const deployedCount = computed(() => {
            return Object.values(myBoard.value).filter(v => v !== null).length;
        });
        
        onMounted(initBoard);
        
        return {
            myBoard, selectedNumber, showTutorial, deployedCount,
            selectNumber, placeNumber, clearCell, getAvailableNumbers
        };
    },
    template: `
        <div class="container">
            <div class="flex justify-between items-center mb-4">
                <h2>离线模式 - 新手教学</h2>
                <router-link to="/" class="btn btn-secondary">返回首页</router-link>
            </div>
            
            <div v-if="showTutorial" class="card">
                <h3 class="card-title">欢迎来到魔丸小游戏！</h3>
                <p>这是离线模式，你可以：</p>
                <ul style="margin-left: 20px; color: var(--text-muted);">
                    <li>练习数字部署</li>
                    <li>熟悉棋盘布局</li>
                    <li>了解游戏规则</li>
                </ul>
                <button @click="showTutorial = false" class="btn btn-primary mt-4">开始练习</button>
            </div>
            
            <div v-else class="card">
                <h3 class="card-title">部署练习 ({{ deployedCount }}/10)</h3>
                <p class="text-muted mb-4">选择数字后点击格子放置，再次点击已放置的格子可移除</p>
                
                <div class="game-board">
                    <div v-for="(num, cellId) in myBoard" :key="cellId"
                         :class="['board-cell', { occupied: num !== null }]"
                         @click="num === null ? placeNumber(cellId) : clearCell(cellId)">
                        {{ num !== null ? num : '' }}
                    </div>
                </div>
                
                <div class="number-palette">
                    <button v-for="num in getAvailableNumbers()" :key="num"
                            :class="['number-btn', { selected: selectedNumber === num }]"
                            @click="selectNumber(num)">
                        {{ num }}
                    </button>
                </div>
                
                <div class="mt-4">
                    <h4>对决规则速查</h4>
                    <ul style="color: var(--text-muted);">
                        <li>相同数字 → 同归于尽</li>
                        <li>0 vs 6/9 → 同归于尽</li>
                        <li>8 > 0</li>
                        <li>其他情况：小数字获胜！(0 > 1 > 2 > ... > 9)</li>
                    </ul>
                </div>
            </div>
        </div>
    `
};

// ===== Router =====
const routes = [
    { path: '/', component: HomePage },
    { path: '/login', component: LoginPage },
    { path: '/register', component: RegisterPage },
    { path: '/rooms', component: RoomsPage, meta: { requiresAuth: true } },
    { path: '/room/:id', component: RoomPage, meta: { requiresAuth: true } },
    { path: '/leaderboard', component: LeaderboardPage },
    { path: '/rules', component: RulesPage },
    { path: '/admin', component: AdminPage, meta: { requiresAuth: true } },
    { path: '/offline', component: OfflinePage }
];

const router = createRouter({
    history: createWebHashHistory(),
    routes
});

router.beforeEach((to, from, next) => {
    if (to.meta.requiresAuth && !localStorage.getItem('token')) {
        next('/login');
    } else {
        next();
    }
});

// ===== App =====
const App = {
    components: { AppHeader, ToastContainer },
    template: `
        <div>
            <AppHeader />
            <main style="padding-top: 20px; padding-bottom: 40px;">
                <router-view />
            </main>
            <ToastContainer />
        </div>
    `
};

createApp(App).use(router).mount('#app');
<template>
  <v-app>
    <!-- Шапка -->
    <v-app-bar color="primary">
      <v-app-bar-title>🎫 TicketSystem</v-app-bar-title>
      <v-spacer></v-spacer>

      <!-- Переключатель: Мои заявки / Все заявки -->
      <v-btn-toggle v-model="viewMode" mandatory class="mr-4">
        <v-btn value="my" size="small">
          <v-icon left>mdi-account</v-icon> Мои заявки
        </v-btn>
        <v-btn value="all" size="small">
          <v-icon left>mdi-format-list-bulleted</v-icon> Все заявки
        </v-btn>
      </v-btn-toggle>

      <v-chip color="white" variant="outlined" class="mr-2">
        {{ user?.display_name }} ({{ user?.role?.display_name }})
      </v-chip>
      <v-btn v-if="canCreate" color="success" class="mr-2" @click="openCreate">
        <v-icon left>mdi-plus</v-icon> Создать
      </v-btn>
      <v-btn v-if="isAdmin" variant="text" @click="openAdmin">
        <v-icon>mdi-account-cog</v-icon>
      </v-btn>
      <v-btn icon @click="logout">
        <v-icon>mdi-logout</v-icon>
      </v-btn>
    </v-app-bar>

    <v-main>
      <v-container fluid>
        <v-alert v-if="isReader" type="info" class="mb-4">
          Вы читатель. Обратитесь к администратору для получения роли.
        </v-alert>

        <v-row>
          <!-- Левая панель: список заявок -->
          <v-col cols="4">
            <v-card>
              <v-card-title class="d-flex align-center">
                <span v-if="viewMode === 'my'"
                  >Мои заявки ({{ tickets.length }})</span
                >
                <span v-else>Все заявки ({{ tickets.length }})</span>
                <v-spacer></v-spacer>
                <v-btn icon size="small" @click="loadTickets">
                  <v-icon>mdi-refresh</v-icon>
                </v-btn>
              </v-card-title>

              <!-- Фильтры (только для "Все заявки") -->
              <v-card-text v-if="viewMode === 'all'" class="pb-0">
                <v-text-field
                  v-model="filters.search"
                  label="Поиск по ключу или названию"
                  prepend-inner-icon="mdi-magnify"
                  density="compact"
                  clearable
                  hide-details
                  class="mb-2"
                  @update:model-value="debouncedSearch"
                ></v-text-field>

                <v-row dense>
                  <v-col cols="6">
                    <v-select
                      v-model="filters.status"
                      :items="statusOptions"
                      label="Статус"
                      density="compact"
                      clearable
                      hide-details
                      @update:model-value="loadTickets"
                    ></v-select>
                  </v-col>
                  <v-col cols="6">
                    <v-select
                      v-model="filters.priority"
                      :items="priorityOptions"
                      label="Приоритет"
                      density="compact"
                      clearable
                      hide-details
                      @update:model-value="loadTickets"
                    ></v-select>
                  </v-col>
                </v-row>
              </v-card-text>

              <v-divider class="mt-2"></v-divider>

              <!-- Список заявок -->
              <v-list
                density="compact"
                v-if="tickets.length"
                class="overflow-y-auto"
                style="max-height: 60vh"
              >
                <v-list-item
                  v-for="t in tickets"
                  :key="t.id"
                  @click="selectTicket(t)"
                  :class="{ 'bg-blue-lighten-4': cur && cur.key === t.key }"
                >
                  <template v-slot:prepend>
                    <v-chip
                      size="x-small"
                      :color="statusColor(t.status)"
                      class="mr-2"
                    >
                      {{ statusLabel(t.status) }}
                    </v-chip>
                  </template>
                  <v-list-item-title class="font-weight-bold">{{
                    t.key
                  }}</v-list-item-title>
                  <v-list-item-subtitle>{{ t.title }}</v-list-item-subtitle>
                  <template v-slot:append>
                    <div class="d-flex flex-column align-end">
                      <v-chip size="x-small" :color="priorityColor(t.priority)">
                        {{ priorityLabel(t.priority) }}
                      </v-chip>
                      <span class="text-caption text-grey mt-1">
                        {{ t.assignee?.display_name || "Не назначен" }}
                      </span>
                    </div>
                  </template>
                </v-list-item>
              </v-list>
              <v-card-text v-else class="text-center text-grey">
                <v-icon size="48" color="grey-lighten-1"
                  >mdi-ticket-outline</v-icon
                >
                <div class="mt-2">
                  {{
                    viewMode === "my"
                      ? "У вас нет активных заявок"
                      : "Заявки не найдены"
                  }}
                </div>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- Правая панель: детали заявки -->
          <v-col cols="8">
            <v-card v-if="cur">
              <v-card-title class="d-flex align-center">
                <v-chip
                  :color="cur.role?.prefix ? 'primary' : 'grey'"
                  class="mr-2"
                >
                  {{ cur.key }}
                </v-chip>
                <span>{{ cur.title }}</span>
              </v-card-title>

              <v-card-text>
                <!-- Редактируемые поля -->
                <v-row v-if="canEdit">
                  <v-col cols="3">
                    <v-select
                      v-model="cur.status"
                      :items="statusOptions.filter((s) => s.value)"
                      item-title="title"
                      item-value="value"
                      label="Статус"
                      @update:model-value="updateStatus"
                      density="compact"
                    ></v-select>
                  </v-col>
                  <v-col cols="3">
                    <v-select
                      v-model="cur.priority"
                      :items="priorityOptions.filter((p) => p.value)"
                      item-title="title"
                      item-value="value"
                      label="Приоритет"
                      @update:model-value="updateTicket"
                      density="compact"
                    ></v-select>
                  </v-col>
                  <v-col cols="3">
                    <v-autocomplete
                      v-model="cur.assignee_id"
                      :items="users"
                      item-title="display_name"
                      item-value="id"
                      label="Исполнитель"
                      @update:model-value="updateTicket"
                      density="compact"
                      clearable
                    ></v-autocomplete>
                  </v-col>
                  <v-col cols="3">
                    <div class="text-caption text-grey">Тип заявки</div>
                    <v-chip size="small">{{ cur.role?.display_name }}</v-chip>
                  </v-col>
                </v-row>

                <!-- Только просмотр для читателей -->
                <v-row v-else>
                  <v-col cols="3">
                    <div class="text-caption text-grey">Статус</div>
                    <v-chip :color="statusColor(cur.status)">{{
                      statusLabel(cur.status)
                    }}</v-chip>
                  </v-col>
                  <v-col cols="3">
                    <div class="text-caption text-grey">Приоритет</div>
                    <v-chip :color="priorityColor(cur.priority)">{{
                      priorityLabel(cur.priority)
                    }}</v-chip>
                  </v-col>
                  <v-col cols="3">
                    <div class="text-caption text-grey">Исполнитель</div>
                    <span>{{
                      cur.assignee?.display_name || "Не назначен"
                    }}</span>
                  </v-col>
                  <v-col cols="3">
                    <div class="text-caption text-grey">Тип</div>
                    <v-chip size="small">{{ cur.role?.display_name }}</v-chip>
                  </v-col>
                </v-row>

                <v-divider class="my-4"></v-divider>

                <!-- Описание -->
                <div class="text-subtitle-2 mb-2">Описание</div>
                <div class="text-body-1 pa-3 bg-grey-lighten-4 rounded">
                  {{ cur.description || "Нет описания" }}
                </div>

                <v-divider class="my-4"></v-divider>

                <!-- Метаданные -->
                <v-row>
                  <v-col cols="4">
                    <div class="text-caption text-grey">Автор</div>
                    <span>{{ cur.author?.display_name }}</span>
                  </v-col>
                  <v-col cols="4">
                    <div class="text-caption text-grey">Создано</div>
                    <span>{{ formatDate(cur.created_at) }}</span>
                  </v-col>
                  <v-col cols="4">
                    <div class="text-caption text-grey">Время в работе</div>
                    <span>{{ formatTime(cur.time_spent) }}</span>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>

            <!-- Пустое состояние -->
            <v-card v-else>
              <v-card-text class="text-center text-grey py-16">
                <v-icon size="80" color="grey-lighten-1"
                  >mdi-ticket-outline</v-icon
                >
                <div class="text-h6 mt-4">Выберите заявку из списка</div>
                <div class="mt-2">Или создайте новую</div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </v-main>

    <!-- Диалог создания заявки -->
    <v-dialog v-model="showCreate" max-width="600">
      <v-card>
        <v-card-title>Создать заявку</v-card-title>
        <v-card-text>
          <v-select
            v-model="newTicket.role_id"
            :items="roles"
            item-title="display_name"
            item-value="id"
            label="Тип заявки"
          ></v-select>
          <v-text-field
            v-model="newTicket.title"
            label="Название"
            class="mt-2"
            :rules="[(v) => !!v || 'Обязательное поле']"
          ></v-text-field>
          <v-textarea
            v-model="newTicket.description"
            label="Описание"
            rows="4"
          ></v-textarea>
          <v-row>
            <v-col cols="6">
              <v-select
                v-model="newTicket.priority"
                :items="priorityOptions.filter((p) => p.value)"
                item-title="title"
                item-value="value"
                label="Приоритет"
              ></v-select>
            </v-col>
            <v-col cols="6">
              <v-autocomplete
                v-model="newTicket.assignee_id"
                :items="users"
                item-title="display_name"
                item-value="id"
                label="Исполнитель"
                clearable
              ></v-autocomplete>
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="showCreate = false">Отмена</v-btn>
          <v-btn
            color="primary"
            @click="createTicket"
            :disabled="!newTicket.title"
          >
            Создать
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Админ-панель -->
    <v-dialog v-model="showAdmin" max-width="900">
      <v-card>
        <v-card-title class="d-flex align-center">
          <span>Управление пользователями</span>
          <v-spacer></v-spacer>
          <v-btn icon size="small" @click="loadUsers">
            <v-icon>mdi-refresh</v-icon>
          </v-btn>
        </v-card-title>
        <v-card-text>
          <v-table v-if="allUsers.length">
            <thead>
              <tr>
                <th>ID</th>
                <th>Логин</th>
                <th>Имя</th>
                <th>Роль</th>
                <th>Статус</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="u in allUsers"
                :key="u.id"
                :class="{ 'text-grey': !u.is_active }"
              >
                <td>{{ u.id }}</td>
                <td>{{ u.login }}</td>
                <td>{{ u.display_name }}</td>
                <td>
                  <v-select
                    v-model="u.newRoleId"
                    :items="allRoles"
                    item-title="display_name"
                    item-value="id"
                    density="compact"
                    hide-details
                    variant="outlined"
                    style="min-width: 180px"
                  ></v-select>
                </td>
                <td>
                  <v-chip :color="u.is_active ? 'green' : 'red'" size="small">
                    {{ u.is_active ? "Активен" : "Заблокирован" }}
                  </v-chip>
                </td>
                <td>
                  <v-btn
                    size="small"
                    color="primary"
                    class="mr-1"
                    @click="changeRole(u)"
                    :disabled="u.newRoleId === u.role.id"
                  >
                    Сохранить
                  </v-btn>
                  <v-btn
                    size="small"
                    :color="u.is_active ? 'warning' : 'success'"
                    @click="toggleUserStatus(u)"
                    :disabled="u.id === user?.id"
                  >
                    {{ u.is_active ? "Блок" : "Разблок" }}
                  </v-btn>
                </td>
              </tr>
            </tbody>
          </v-table>
          <div v-else class="text-center py-4">Загрузка...</div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="showAdmin = false">Закрыть</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Снэкбар -->
    <v-snackbar v-model="snackbar" :color="snackbarColor" timeout="3000">
      {{ snackbarText }}
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import api from "../api";

const router = useRouter();
const authStore = useAuthStore();

// ========== СОСТОЯНИЕ ==========

const user = ref(null);
const viewMode = ref("my"); // "my" или "all"

// Заявки
const tickets = ref([]);
const cur = ref(null);

// Фильтры для "Все заявки"
const filters = ref({
  search: "",
  status: null,
  priority: null,
});

// Справочники
const roles = ref([]);
const users = ref([]);
const allUsers = ref([]);
const allRoles = ref([]);

// Диалоги
const showCreate = ref(false);
const showAdmin = ref(false);

// Форма создания
const newTicket = ref({
  title: "",
  description: "",
  priority: "medium",
  role_id: null,
  assignee_id: null,
});

// Уведомления
const snackbar = ref(false);
const snackbarText = ref("");
const snackbarColor = ref("success");

// Опции для селектов
const statusOptions = [
  { title: "Все", value: null },
  { title: "Открыта", value: "open" },
  { title: "В работе", value: "in_progress" },
  { title: "Ожидание", value: "waiting" },
  { title: "Готово", value: "done" },
  { title: "Закрыта", value: "closed" },
];

const priorityOptions = [
  { title: "Все", value: null },
  { title: "Низкий", value: "low" },
  { title: "Средний", value: "medium" },
  { title: "Высокий", value: "high" },
  { title: "Критический", value: "critical" },
];

// ========== ВЫЧИСЛЯЕМЫЕ ==========

const isAdmin = computed(() => user.value?.role?.is_admin);
const isReader = computed(() => user.value?.role?.name === "reader");
const canCreate = computed(
  () => !isReader.value && (user.value?.role?.prefix || isAdmin.value),
);
const canEdit = computed(() => !isReader.value);

// ========== МЕТОДЫ ==========

function notify(text, color = "success") {
  snackbarText.value = text;
  snackbarColor.value = color;
  snackbar.value = true;
}

function formatDate(dateStr) {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString("ru-RU");
}

function formatTime(seconds) {
  if (!seconds) return "0 мин";
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  if (hours > 0) return `${hours} ч ${mins} мин`;
  return `${mins} мин`;
}

function statusColor(s) {
  const colors = {
    open: "grey",
    in_progress: "blue",
    waiting: "orange",
    done: "green",
    closed: "grey-darken-2",
  };
  return colors[s] || "grey";
}

function statusLabel(s) {
  const labels = {
    open: "Открыта",
    in_progress: "В работе",
    waiting: "Ожидание",
    done: "Готово",
    closed: "Закрыта",
  };
  return labels[s] || s;
}

function priorityColor(p) {
  const colors = {
    low: "green",
    medium: "yellow-darken-2",
    high: "orange",
    critical: "red",
  };
  return colors[p] || "grey";
}

function priorityLabel(p) {
  const labels = {
    low: "Низкий",
    medium: "Средний",
    high: "Высокий",
    critical: "Критический",
  };
  return labels[p] || p;
}

// ========== ЗАГРУЗКА ДАННЫХ ==========

onMounted(async () => {
  try {
    const r = await api.get("/auth/me");
    user.value = r.data;
    authStore.user = r.data;

    const usersResp = await api.get("/tickets/users");
    users.value = usersResp.data;

    const rolesResp = await api.get("/users/roles");
    allRoles.value = rolesResp.data;

    await loadTickets();
  } catch (e) {
    console.error("Error loading data:", e);
    if (e.response?.status === 401) {
      logout();
    }
  }
});

// Следим за переключением режима
watch(viewMode, () => {
  cur.value = null;
  loadTickets();
});

// Загрузка заявок
async function loadTickets() {
  try {
    let url = viewMode.value === "my" ? "/tickets/my" : "/tickets";

    // Добавляем фильтры для "Все заявки"
    if (viewMode.value === "all") {
      const params = new URLSearchParams();
      if (filters.value.search) params.append("search", filters.value.search);
      if (filters.value.status) params.append("status", filters.value.status);
      if (filters.value.priority)
        params.append("priority", filters.value.priority);
      if (params.toString()) url += "?" + params.toString();
    }

    const r = await api.get(url);
    tickets.value = r.data;
  } catch (e) {
    notify("Ошибка загрузки заявок", "error");
  }
}

// Дебаунс для поиска
let searchTimeout = null;
function debouncedSearch() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    loadTickets();
  }, 300);
}

// Выбрать заявку
async function selectTicket(t) {
  try {
    const r = await api.get("/tickets/" + t.key);
    cur.value = {
      ...r.data,
      assignee_id: r.data.assignee?.id,
    };
  } catch (e) {
    notify("Ошибка загрузки заявки", "error");
  }
}

// ========== СОЗДАНИЕ ЗАЯВКИ ==========

async function openCreate() {
  try {
    const r = await api.get("/tickets/roles");
    roles.value = r.data;
    if (roles.value.length) {
      newTicket.value.role_id = roles.value[0].id;
    }
    newTicket.value.title = "";
    newTicket.value.description = "";
    newTicket.value.priority = "medium";
    newTicket.value.assignee_id = null;
    showCreate.value = true;
  } catch (e) {
    notify("Ошибка загрузки ролей", "error");
  }
}

async function createTicket() {
  try {
    const result = await api.post("/tickets", newTicket.value);
    showCreate.value = false;
    notify(`Заявка ${result.data.key} создана!`);
    await loadTickets();
    // Выбираем созданную заявку
    await selectTicket(result.data);
  } catch (e) {
    notify(e.response?.data?.detail || "Ошибка создания", "error");
  }
}

// ========== ОБНОВЛЕНИЕ ЗАЯВКИ ==========

async function updateStatus() {
  try {
    await api.patch("/tickets/" + cur.value.key + "/status", {
      status: cur.value.status,
    });
    notify("Статус обновлён");
    await loadTickets();
  } catch (e) {
    notify("Ошибка обновления статуса", "error");
  }
}

async function updateTicket() {
  try {
    await api.patch("/tickets/" + cur.value.key, {
      assignee_id: cur.value.assignee_id,
      priority: cur.value.priority,
    });
    notify("Заявка обновлена");
    await loadTickets();
  } catch (e) {
    notify("Ошибка обновления", "error");
  }
}

// ========== АДМИН-ФУНКЦИИ ==========

async function openAdmin() {
  showAdmin.value = true;
  await loadUsers();
}

async function loadUsers() {
  try {
    const r = await api.get("/users");
    allUsers.value = r.data.map((u) => ({
      ...u,
      newRoleId: u.role.id,
    }));
  } catch (e) {
    notify("Ошибка загрузки пользователей", "error");
  }
}

async function changeRole(u) {
  try {
    await api.patch("/users/" + u.id + "/role", { role_id: u.newRoleId });
    notify(`Роль пользователя ${u.login} изменена`);
    await loadUsers();
  } catch (e) {
    notify(e.response?.data?.detail || "Ошибка", "error");
  }
}

async function toggleUserStatus(u) {
  try {
    await api.patch("/users/" + u.id + "/status", { is_active: !u.is_active });
    notify(
      `Пользователь ${u.login} ${u.is_active ? "заблокирован" : "разблокирован"}`,
    );
    await loadUsers();
  } catch (e) {
    notify(e.response?.data?.detail || "Ошибка", "error");
  }
}

// ========== ВЫХОД ==========

function logout() {
  authStore.logout();
  router.push("/login");
}
</script>

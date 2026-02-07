<template>
  <v-app>
    <v-app-bar color="primary">
      <v-app-bar-title>🎫 TicketSystem</v-app-bar-title>
      <v-spacer></v-spacer>
      <v-chip color="white" variant="outlined" class="mr-2">
        {{ user?.display_name }} ({{ user?.role?.display_name }})
      </v-chip>
      <v-btn v-if="canCreate" color="success" class="mr-2" @click="openCreate">
        <v-icon left>mdi-plus</v-icon> Создать
      </v-btn>
      <v-btn v-if="isAdmin" variant="text" @click="openAdmin">
        <v-icon left>mdi-account-cog</v-icon> Пользователи
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
          <!-- Список заявок -->
          <v-col cols="4">
            <v-card>
              <v-card-title class="d-flex align-center">
                <span>Заявки ({{ tickets.length }})</span>
                <v-spacer></v-spacer>
                <v-btn icon size="small" @click="fetchAll">
                  <v-icon>mdi-refresh</v-icon>
                </v-btn>
              </v-card-title>
              <v-list density="compact" v-if="tickets.length">
                <v-list-item
                  v-for="t in tickets"
                  :key="t.id"
                  @click="sel(t)"
                  :class="{ 'bg-blue-lighten-4': cur && cur.key === t.key }"
                >
                  <template v-slot:prepend>
                    <v-chip size="x-small" :color="statusColor(t.status)">{{
                      t.status
                    }}</v-chip>
                  </template>
                  <v-list-item-title>{{ t.key }}</v-list-item-title>
                  <v-list-item-subtitle>{{ t.title }}</v-list-item-subtitle>
                  <template v-slot:append>
                    <v-chip size="x-small" :color="priorityColor(t.priority)">{{
                      t.priority
                    }}</v-chip>
                  </template>
                </v-list-item>
              </v-list>
              <v-card-text v-else class="text-center text-grey">
                Нет заявок
              </v-card-text>
            </v-card>
          </v-col>

          <!-- Детали заявки -->
          <v-col cols="8">
            <v-card v-if="cur">
              <v-card-title>{{ cur.key }}: {{ cur.title }}</v-card-title>
              <v-card-text>
                <v-row v-if="canEdit">
                  <v-col cols="4">
                    <v-select
                      v-model="cur.status"
                      :items="statuses"
                      label="Статус"
                      @update:model-value="updateStatus"
                      density="compact"
                    ></v-select>
                  </v-col>
                  <v-col cols="4">
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
                  <v-col cols="4">
                    <v-chip :color="priorityColor(cur.priority)" class="mr-2">{{
                      cur.priority
                    }}</v-chip>
                    <v-chip>{{
                      cur.role?.prefix || cur.role?.display_name
                    }}</v-chip>
                  </v-col>
                </v-row>
                <div v-else>
                  <p><b>Статус:</b> {{ cur.status }}</p>
                  <p><b>Автор:</b> {{ cur.author?.display_name }}</p>
                  <p>
                    <b>Исполнитель:</b> {{ cur.assignee?.display_name || "-" }}
                  </p>
                </div>

                <v-divider class="my-4"></v-divider>

                <div class="text-subtitle-2 mb-2">Описание:</div>
                <p class="text-body-1">
                  {{ cur.description || "Нет описания" }}
                </p>

                <v-divider class="my-4"></v-divider>

                <div class="text-caption text-grey">
                  Создано: {{ formatDate(cur.created_at) }} | Автор:
                  {{ cur.author?.display_name }}
                </div>
              </v-card-text>
            </v-card>
            <v-card v-else>
              <v-card-text class="text-center text-grey py-10">
                <v-icon size="64" color="grey-lighten-1"
                  >mdi-ticket-outline</v-icon
                >
                <div class="mt-4">Выберите заявку из списка</div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </v-main>

    <!-- Диалог создания заявки -->
    <v-dialog v-model="showCreate" max-width="500">
      <v-card>
        <v-card-title>Создать заявку</v-card-title>
        <v-card-text>
          <v-select
            v-model="newRoleId"
            :items="roles"
            item-title="display_name"
            item-value="id"
            label="Тип заявки"
          ></v-select>
          <v-text-field
            v-model="newTitle"
            label="Название"
            class="mt-2"
          ></v-text-field>
          <v-textarea v-model="newDesc" label="Описание" rows="3"></v-textarea>
          <v-select
            v-model="newPriority"
            :items="priorities"
            label="Приоритет"
          ></v-select>
          <v-autocomplete
            v-model="newAssigneeId"
            :items="users"
            item-title="display_name"
            item-value="id"
            label="Исполнитель"
            clearable
          ></v-autocomplete>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="showCreate = false">Отмена</v-btn>
          <v-btn color="primary" @click="createTicket" :disabled="!newTitle"
            >Создать</v-btn
          >
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Админ-панель: управление пользователями -->
    <v-dialog v-model="showAdmin" max-width="800">
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

    <!-- Снэкбар для уведомлений -->
    <v-snackbar v-model="snackbar" :color="snackbarColor" timeout="3000">
      {{ snackbarText }}
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import api from "../api";

const router = useRouter();
const authStore = useAuthStore();

// Данные пользователя
const user = ref(null);

// Заявки
const tickets = ref([]);
const cur = ref(null);

// Справочники
const roles = ref([]);
const users = ref([]);
const allUsers = ref([]);
const allRoles = ref([]);

// Диалоги
const showCreate = ref(false);
const showAdmin = ref(false);

// Форма создания
const newTitle = ref("");
const newDesc = ref("");
const newPriority = ref("medium");
const newRoleId = ref(null);
const newAssigneeId = ref(null);

// Константы
const priorities = ["low", "medium", "high", "critical"];
const statuses = ["open", "in_progress", "waiting", "done", "closed"];

// Уведомления
const snackbar = ref(false);
const snackbarText = ref("");
const snackbarColor = ref("success");

// Вычисляемые свойства
const isAdmin = computed(() => user.value?.role?.is_admin);
const isReader = computed(() => user.value?.role?.name === "reader");
const canCreate = computed(
  () => !isReader.value && (user.value?.role?.prefix || isAdmin.value),
);
const canEdit = computed(() => !isReader.value);

// Показать уведомление
function notify(text, color = "success") {
  snackbarText.value = text;
  snackbarColor.value = color;
  snackbar.value = true;
}

// Форматирование даты
function formatDate(dateStr) {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString("ru-RU");
}

// Загрузка при монтировании
onMounted(async () => {
  try {
    // Загружаем текущего пользователя
    const r = await api.get("/auth/me");
    user.value = r.data;

    // Обновляем authStore
    authStore.user = r.data;

    // Загружаем справочники
    const usersResp = await api.get("/tickets/users");
    users.value = usersResp.data;

    const rolesResp = await api.get("/users/roles");
    allRoles.value = rolesResp.data;

    // Загружаем заявки
    await fetchAll();
  } catch (e) {
    console.error("Error loading data:", e);
    if (e.response?.status === 401) {
      logout();
    }
  }
});

// Загрузить все заявки
async function fetchAll() {
  try {
    const r = await api.get("/tickets");
    tickets.value = r.data;
  } catch (e) {
    notify("Ошибка загрузки заявок", "error");
  }
}

// Выбрать заявку
async function sel(t) {
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

// Открыть диалог создания
async function openCreate() {
  try {
    const r = await api.get("/tickets/roles");
    roles.value = r.data;
    if (roles.value.length) {
      newRoleId.value = roles.value[0].id;
    }
    newTitle.value = "";
    newDesc.value = "";
    newPriority.value = "medium";
    newAssigneeId.value = null;
    showCreate.value = true;
  } catch (e) {
    notify("Ошибка загрузки ролей", "error");
  }
}

// Создать заявку
async function createTicket() {
  try {
    await api.post("/tickets", {
      title: newTitle.value,
      description: newDesc.value,
      priority: newPriority.value,
      role_id: newRoleId.value,
      assignee_id: newAssigneeId.value,
    });
    showCreate.value = false;
    notify("Заявка создана!");
    await fetchAll();
  } catch (e) {
    notify(e.response?.data?.detail || "Ошибка создания", "error");
  }
}

// Обновить статус
async function updateStatus() {
  try {
    await api.patch("/tickets/" + cur.value.key + "/status", {
      status: cur.value.status,
    });
    notify("Статус обновлён");
    await fetchAll();
  } catch (e) {
    notify("Ошибка обновления статуса", "error");
  }
}

// Обновить заявку
async function updateTicket() {
  try {
    await api.patch("/tickets/" + cur.value.key, {
      assignee_id: cur.value.assignee_id,
    });
    notify("Заявка обновлена");
    await fetchAll();
  } catch (e) {
    notify("Ошибка обновления", "error");
  }
}

// ========== АДМИН-ФУНКЦИИ ==========

// Открыть админ-панель
async function openAdmin() {
  showAdmin.value = true;
  await loadUsers();
}

// Загрузить пользователей
async function loadUsers() {
  try {
    const r = await api.get("/users");
    // Добавляем newRoleId для отслеживания изменений
    allUsers.value = r.data.map((u) => ({
      ...u,
      newRoleId: u.role.id,
    }));
  } catch (e) {
    notify("Ошибка загрузки пользователей", "error");
  }
}

// Изменить роль
async function changeRole(u) {
  try {
    await api.patch("/users/" + u.id + "/role", {
      role_id: u.newRoleId,
    });
    notify(`Роль пользователя ${u.login} изменена`);
    await loadUsers();
  } catch (e) {
    notify(e.response?.data?.detail || "Ошибка изменения роли", "error");
  }
}

// Заблокировать/разблокировать пользователя
async function toggleUserStatus(u) {
  try {
    await api.patch("/users/" + u.id + "/status", {
      is_active: !u.is_active,
    });
    notify(
      `Пользователь ${u.login} ${u.is_active ? "заблокирован" : "разблокирован"}`,
    );
    await loadUsers();
  } catch (e) {
    notify(e.response?.data?.detail || "Ошибка", "error");
  }
}

// ========== ЦВЕТА ==========

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

function priorityColor(p) {
  const colors = {
    low: "green",
    medium: "yellow-darken-2",
    high: "orange",
    critical: "red",
  };
  return colors[p] || "grey";
}

// ========== ВЫХОД ==========

function logout() {
  authStore.logout();
  router.push("/login");
}
</script>

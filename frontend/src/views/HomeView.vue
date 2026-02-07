<template>
  <v-app>
    <!-- Шапка -->
    <v-app-bar color="primary">
      <v-app-bar-title>🎫 Gerask</v-app-bar-title>
      <v-spacer></v-spacer>

      <v-btn-toggle v-model="viewMode" mandatory class="mr-4">
        <v-btn value="my" size="small">
          <v-icon start>mdi-account</v-icon> Мои заявки
        </v-btn>
        <v-btn value="all" size="small">
          <v-icon start>mdi-format-list-bulleted</v-icon> Все заявки
        </v-btn>
      </v-btn-toggle>

      <v-chip color="white" variant="outlined" class="mr-2">
        {{ user?.display_name }} ({{ user?.role?.display_name }})
      </v-chip>
      <v-btn v-if="canCreate" color="success" class="mr-2" @click="openCreate">
        <v-icon start>mdi-plus</v-icon> Создать
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

              <!-- Фильтры -->
              <v-card-text v-if="viewMode === 'all'" class="pb-0">
                <v-text-field
                  v-model="filters.search"
                  label="Поиск"
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
                      :items="statusFilterOptions"
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
                      :items="priorityFilterOptions"
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

              <v-list
                density="compact"
                v-if="tickets.length"
                class="overflow-y-auto"
                style="max-height: 70vh"
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
                    <v-chip size="x-small" :color="priorityColor(t.priority)">
                      {{ priorityLabel(t.priority) }}
                    </v-chip>
                  </template>
                </v-list-item>
              </v-list>
              <v-card-text v-else class="text-center text-grey">
                <v-icon size="48" color="grey-lighten-1"
                  >mdi-ticket-outline</v-icon
                >
                <div class="mt-2">Нет заявок</div>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- Правая панель: детали заявки -->
          <v-col cols="8">
            <v-card v-if="cur">
              <!-- Заголовок -->
              <v-card-title class="d-flex align-center">
                <v-chip
                  :color="cur.role?.prefix ? 'primary' : 'grey'"
                  class="mr-2"
                >
                  {{ cur.key }}
                </v-chip>
                <span class="flex-grow-1">{{ cur.title }}</span>

                <!-- Меню действий -->
                <v-menu v-if="canEdit">
                  <template v-slot:activator="{ props }">
                    <v-btn icon v-bind="props" variant="text">
                      <v-icon>mdi-dots-vertical</v-icon>
                    </v-btn>
                  </template>
                  <v-list density="compact">
                    <v-list-item @click="openEditTitle">
                      <v-list-item-title
                        ><v-icon start>mdi-pencil</v-icon> Изменить
                        название</v-list-item-title
                      >
                    </v-list-item>
                    <v-list-item @click="openEditDescription">
                      <v-list-item-title
                        ><v-icon start>mdi-text</v-icon> Изменить
                        описание</v-list-item-title
                      >
                    </v-list-item>
                    <v-divider></v-divider>
                    <v-list-item @click="openTransfer">
                      <v-list-item-title
                        ><v-icon start>mdi-account-arrow-right</v-icon> Передать
                        исполнителю</v-list-item-title
                      >
                    </v-list-item>
                  </v-list>
                </v-menu>
              </v-card-title>

              <v-card-text>
                <!-- Статус и таймер -->
                <v-row align="center" class="mb-4">
                  <v-col cols="auto">
                    <v-chip
                      :color="statusColor(cur.status)"
                      size="large"
                      class="font-weight-bold"
                    >
                      {{ statusLabel(cur.status) }}
                    </v-chip>
                  </v-col>

                  <!-- Секундомер -->
                  <v-col
                    cols="auto"
                    v-if="cur.status === 'in_progress' || cur.time_spent > 0"
                  >
                    <v-chip color="blue-grey" variant="outlined" size="large">
                      <v-icon start>mdi-timer</v-icon>
                      {{ liveTimer }}
                    </v-chip>
                  </v-col>

                  <v-spacer></v-spacer>

                  <!-- Кнопки действий -->
                  <v-col cols="auto" v-if="isAssignee">
                    <v-btn
                      v-if="cur.status === 'open'"
                      color="primary"
                      @click="startWork"
                      :loading="actionLoading"
                    >
                      <v-icon start>mdi-play</v-icon> Взять в работу
                    </v-btn>
                    <v-btn
                      v-if="cur.status === 'in_progress'"
                      color="success"
                      @click="resolveTicket"
                      :loading="actionLoading"
                    >
                      <v-icon start>mdi-check</v-icon> Решение запроса
                    </v-btn>
                    <v-btn
                      v-if="cur.status === 'done'"
                      color="warning"
                      @click="reopenTicket"
                      :loading="actionLoading"
                    >
                      <v-icon start>mdi-restart</v-icon> Вернуть в работу
                    </v-btn>
                  </v-col>
                </v-row>

                <!-- Информация -->
                <v-row>
                  <v-col cols="3">
                    <div class="text-caption text-grey">Приоритет</div>
                    <v-select
                      v-if="canEdit"
                      v-model="cur.priority"
                      :items="priorityOptions"
                      item-title="title"
                      item-value="value"
                      density="compact"
                      hide-details
                      @update:model-value="
                        updateField('priority', cur.priority)
                      "
                    ></v-select>
                    <v-chip
                      v-else
                      :color="priorityColor(cur.priority)"
                      size="small"
                    >
                      {{ priorityLabel(cur.priority) }}
                    </v-chip>
                  </v-col>
                  <v-col cols="3">
                    <div class="text-caption text-grey">Тип заявки</div>
                    <v-chip size="small">{{ cur.role?.display_name }}</v-chip>
                  </v-col>
                  <v-col cols="3">
                    <div class="text-caption text-grey">Автор</div>
                    <span>{{ cur.author?.display_name }}</span>
                  </v-col>
                  <v-col cols="3">
                    <div class="text-caption text-grey">Исполнитель</div>
                    <v-autocomplete
                      v-if="canEdit"
                      v-model="cur.assignee_id"
                      :items="users"
                      item-title="display_name"
                      item-value="id"
                      density="compact"
                      hide-details
                      clearable
                      @update:model-value="
                        updateField('assignee_id', cur.assignee_id)
                      "
                    ></v-autocomplete>
                    <span v-else>{{
                      cur.assignee?.display_name || "Не назначен"
                    }}</span>
                  </v-col>
                </v-row>

                <v-divider class="my-4"></v-divider>

                <!-- Описание -->
                <div class="text-subtitle-2 mb-2">Описание</div>
                <div
                  class="text-body-1 pa-3 bg-grey-lighten-4 rounded"
                  style="min-height: 80px"
                >
                  {{ cur.description || "Нет описания" }}
                </div>

                <v-divider class="my-4"></v-divider>

                <!-- Метаданные -->
                <v-row class="text-caption">
                  <v-col cols="3">
                    <span class="text-grey">Создано:</span><br />
                    {{ formatDate(cur.created_at) }}
                  </v-col>
                  <v-col cols="3">
                    <span class="text-grey">Решено:</span><br />
                    {{ cur.resolved_at ? formatDate(cur.resolved_at) : "-" }}
                  </v-col>
                  <v-col cols="3">
                    <span class="text-grey">Время в работе:</span><br />
                    {{ formatTime(cur.time_spent) }}
                  </v-col>
                  <v-col cols="3">
                    <span class="text-grey">Дедлайн:</span><br />
                    {{ cur.deadline ? formatDate(cur.deadline) : "-" }}
                  </v-col>
                </v-row>

                <v-divider class="my-4"></v-divider>

                <!-- ⭐ ВКЛАДКИ: Комментарии и История -->
                <v-tabs v-model="activeTab" color="primary">
                  <v-tab value="comments">
                    <v-icon start>mdi-comment-multiple</v-icon>
                    Комментарии ({{ comments.length }})
                  </v-tab>
                  <v-tab value="history">
                    <v-icon start>mdi-history</v-icon>
                    История изменений
                  </v-tab>
                </v-tabs>

                <v-window v-model="activeTab" class="mt-4">
                  <!-- Вкладка: Комментарии -->
                  <v-window-item value="comments">
                    <!-- Список комментариев -->
                    <div
                      v-if="comments.length"
                      class="mb-4"
                      style="max-height: 300px; overflow-y: auto"
                    >
                      <v-card
                        v-for="comment in comments"
                        :key="comment.id"
                        variant="outlined"
                        class="mb-2"
                      >
                        <v-card-text class="py-2">
                          <div class="d-flex align-center mb-2">
                            <v-avatar size="32" color="primary" class="mr-2">
                              <span class="text-white text-caption">
                                {{
                                  comment.author?.display_name?.charAt(0) || "?"
                                }}
                              </span>
                            </v-avatar>
                            <div>
                              <strong>{{
                                comment.author?.display_name
                              }}</strong>
                              <div class="text-caption text-grey">
                                {{ formatDate(comment.created_at) }}
                                <span
                                  v-if="
                                    comment.updated_at !== comment.created_at
                                  "
                                  >(ред.)</span
                                >
                              </div>
                            </div>
                            <v-spacer></v-spacer>
                            <v-btn
                              v-if="comment.author?.id === user?.id || isAdmin"
                              icon
                              size="x-small"
                              variant="text"
                              @click="editComment(comment)"
                            >
                              <v-icon size="small">mdi-pencil</v-icon>
                            </v-btn>
                            <v-btn
                              v-if="comment.author?.id === user?.id || isAdmin"
                              icon
                              size="x-small"
                              variant="text"
                              color="error"
                              @click="deleteComment(comment)"
                            >
                              <v-icon size="small">mdi-delete</v-icon>
                            </v-btn>
                          </div>
                          <div
                            v-html="comment.content"
                            class="comment-content"
                          ></div>
                        </v-card-text>
                      </v-card>
                    </div>
                    <div v-else class="text-center text-grey py-4">
                      Комментариев пока нет
                    </div>

                    <!-- Форма добавления комментария -->
                    <v-card variant="outlined" v-if="canEdit">
                      <v-card-text>
                        <div class="d-flex gap-2 mb-2">
                          <v-btn
                            size="x-small"
                            variant="text"
                            @click="formatText('bold')"
                          >
                            <v-icon>mdi-format-bold</v-icon>
                          </v-btn>
                          <v-btn
                            size="x-small"
                            variant="text"
                            @click="formatText('italic')"
                          >
                            <v-icon>mdi-format-italic</v-icon>
                          </v-btn>
                          <v-btn
                            size="x-small"
                            variant="text"
                            @click="formatText('underline')"
                          >
                            <v-icon>mdi-format-underline</v-icon>
                          </v-btn>
                          <v-btn
                            size="x-small"
                            variant="text"
                            @click="formatText('h2')"
                          >
                            <v-icon>mdi-format-header-2</v-icon>
                          </v-btn>
                          <v-btn
                            size="x-small"
                            variant="text"
                            @click="formatText('ul')"
                          >
                            <v-icon>mdi-format-list-bulleted</v-icon>
                          </v-btn>
                          <v-btn
                            size="x-small"
                            variant="text"
                            @click="formatText('code')"
                          >
                            <v-icon>mdi-code-tags</v-icon>
                          </v-btn>
                        </div>
                        <v-textarea
                          ref="commentInput"
                          v-model="newComment"
                          label="Написать комментарий..."
                          rows="3"
                          hide-details
                          variant="outlined"
                        ></v-textarea>
                        <div class="d-flex justify-end mt-2">
                          <v-btn
                            color="primary"
                            @click="addComment"
                            :disabled="!newComment.trim()"
                          >
                            <v-icon start>mdi-send</v-icon> Отправить
                          </v-btn>
                        </div>
                      </v-card-text>
                    </v-card>
                  </v-window-item>

                  <!-- Вкладка: История -->
                  <v-window-item value="history">
                    <div
                      v-if="history.length"
                      style="max-height: 400px; overflow-y: auto"
                    >
                      <v-timeline density="compact" side="end">
                        <v-timeline-item
                          v-for="item in history"
                          :key="item.id"
                          :dot-color="historyColor(item.action)"
                          size="small"
                        >
                          <div class="d-flex align-center">
                            <v-icon
                              :color="historyColor(item.action)"
                              class="mr-2"
                              size="small"
                            >
                              {{ historyIcon(item.action) }}
                            </v-icon>
                            <div>
                              <strong>{{ item.user?.display_name }}</strong>
                              <span class="text-grey">
                                — {{ historyLabel(item.action) }}</span
                              >
                              <div v-if="item.field_name" class="text-caption">
                                {{ item.field_name }}:
                                <span class="text-red">{{
                                  item.old_value || "-"
                                }}</span>
                                →
                                <span class="text-green">{{
                                  item.new_value || "-"
                                }}</span>
                              </div>
                              <div class="text-caption text-grey">
                                {{ formatDate(item.created_at) }}
                              </div>
                            </div>
                          </div>
                        </v-timeline-item>
                      </v-timeline>
                    </div>
                    <div v-else class="text-center text-grey py-4">
                      История пуста
                    </div>
                  </v-window-item>
                </v-window>
              </v-card-text>
            </v-card>

            <!-- Пустое состояние -->
            <v-card v-else>
              <v-card-text class="text-center text-grey py-16">
                <v-icon size="80" color="grey-lighten-1"
                  >mdi-ticket-outline</v-icon
                >
                <div class="text-h6 mt-4">Выберите заявку из списка</div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </v-main>

    <!-- Диалоги -->
    <v-dialog v-model="showEditTitle" max-width="500">
      <v-card>
        <v-card-title>Изменить название</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="editTitle"
            label="Название"
            autofocus
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="showEditTitle = false">Отмена</v-btn>
          <v-btn color="primary" @click="saveTitle">Сохранить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showEditDescription" max-width="600">
      <v-card>
        <v-card-title>Изменить описание</v-card-title>
        <v-card-text>
          <v-textarea
            v-model="editDescription"
            label="Описание"
            rows="6"
            autofocus
          ></v-textarea>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="showEditDescription = false">Отмена</v-btn>
          <v-btn color="primary" @click="saveDescription">Сохранить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showTransfer" max-width="500">
      <v-card>
        <v-card-title>Передать исполнителю</v-card-title>
        <v-card-text>
          <v-autocomplete
            v-model="transferUserId"
            :items="users"
            item-title="display_name"
            item-value="id"
            label="Выберите исполнителя"
            autofocus
          ></v-autocomplete>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="showTransfer = false">Отмена</v-btn>
          <v-btn
            color="primary"
            @click="transferTicket"
            :disabled="!transferUserId"
            >Передать</v-btn
          >
        </v-card-actions>
      </v-card>
    </v-dialog>

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
                :items="priorityOptions"
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
            >Создать</v-btn
          >
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showAdmin" max-width="900">
      <v-card>
        <v-card-title>Управление пользователями</v-card-title>
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
              <tr v-for="u in allUsers" :key="u.id">
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
                  <v-chip :color="u.is_active ? 'green' : 'red'" size="small">{{
                    u.is_active ? "Активен" : "Заблокирован"
                  }}</v-chip>
                </td>
                <td>
                  <v-btn
                    size="small"
                    color="primary"
                    class="mr-1"
                    @click="changeRole(u)"
                    :disabled="u.newRoleId === u.role.id"
                    >Сохранить</v-btn
                  >
                  <v-btn
                    size="small"
                    :color="u.is_active ? 'warning' : 'success'"
                    @click="toggleUserStatus(u)"
                    :disabled="u.id === user?.id"
                    >{{ u.is_active ? "Блок" : "Разблок" }}</v-btn
                  >
                </td>
              </tr>
            </tbody>
          </v-table>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="showAdmin = false">Закрыть</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showEditComment" max-width="600">
      <v-card>
        <v-card-title>Редактировать комментарий</v-card-title>
        <v-card-text>
          <v-textarea
            v-model="editCommentContent"
            rows="4"
            autofocus
          ></v-textarea>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="showEditComment = false">Отмена</v-btn>
          <v-btn color="primary" @click="saveComment">Сохранить</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :color="snackbarColor" timeout="3000">
      {{ snackbarText }}
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import api from "../api";

const router = useRouter();
const authStore = useAuthStore();

// Состояние
const user = ref(null);
const viewMode = ref("my");
const actionLoading = ref(false);
const activeTab = ref("comments");

// Заявки
const tickets = ref([]);
const cur = ref(null);
const comments = ref([]);
const history = ref([]);

// Фильтры
const filters = ref({ search: "", status: null, priority: null });

// Справочники
const roles = ref([]);
const users = ref([]);
const allUsers = ref([]);
const allRoles = ref([]);

// Диалоги
const showCreate = ref(false);
const showAdmin = ref(false);
const showEditTitle = ref(false);
const showEditDescription = ref(false);
const showTransfer = ref(false);
const showEditComment = ref(false);

// Формы
const editTitle = ref("");
const editDescription = ref("");
const transferUserId = ref(null);
const newComment = ref("");
const editCommentContent = ref("");
const editingCommentId = ref(null);
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

// Таймер
const timerInterval = ref(null);
const currentTime = ref(Date.now());

// Опции
const statusFilterOptions = [
  { title: "Все", value: null },
  { title: "Открыта", value: "open" },
  { title: "В работе", value: "in_progress" },
  { title: "Выполнен", value: "done" },
  { title: "Закрыта", value: "closed" },
];
const priorityFilterOptions = [
  { title: "Все", value: null },
  { title: "Низкий", value: "low" },
  { title: "Средний", value: "medium" },
  { title: "Высокий", value: "high" },
  { title: "Критический", value: "critical" },
];
const priorityOptions = [
  { title: "Низкий", value: "low" },
  { title: "Средний", value: "medium" },
  { title: "Высокий", value: "high" },
  { title: "Критический", value: "critical" },
];

// Вычисляемые
const isAdmin = computed(() => user.value?.role?.is_admin);
const isReader = computed(() => user.value?.role?.name === "reader");
const canCreate = computed(
  () => !isReader.value && (user.value?.role?.prefix || isAdmin.value),
);
const canEdit = computed(() => !isReader.value);
const isAssignee = computed(() => {
  if (!cur.value || !user.value) return false;
  return cur.value.assignee_id === user.value.id || isAdmin.value;
});

// Живой таймер
const liveTimer = computed(() => {
  if (!cur.value) return "00:00:00";

  let totalSeconds = cur.value.time_spent || 0;

  if (cur.value.status === "in_progress" && cur.value.timer_started_at) {
    const started = new Date(cur.value.timer_started_at).getTime();
    totalSeconds += Math.floor((currentTime.value - started) / 1000);
  }

  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
});

// Методы
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
  return (
    {
      open: "grey",
      in_progress: "warning",
      done: "success",
      closed: "grey-darken-2",
    }[s] || "grey"
  );
}

function statusLabel(s) {
  return (
    {
      open: "Открыта",
      in_progress: "В работе",
      done: "Выполнен",
      closed: "Закрыта",
    }[s] || s
  );
}

function priorityColor(p) {
  return (
    {
      low: "green",
      medium: "yellow-darken-2",
      high: "orange",
      critical: "red",
    }[p] || "grey"
  );
}

function priorityLabel(p) {
  return (
    {
      low: "Низкий",
      medium: "Средний",
      high: "Высокий",
      critical: "Критический",
    }[p] || p
  );
}

function historyColor(action) {
  const colors = {
    CREATED: "primary",
    STATUS_CHANGED: "warning",
    ASSIGNEE_CHANGED: "info",
    TITLE_CHANGED: "secondary",
    DESCRIPTION_CHANGED: "secondary",
    PRIORITY_CHANGED: "orange",
    COMMENT_ADDED: "success",
  };
  return colors[action] || "grey";
}

function historyIcon(action) {
  const icons = {
    CREATED: "mdi-plus-circle",
    STATUS_CHANGED: "mdi-swap-horizontal",
    ASSIGNEE_CHANGED: "mdi-account-arrow-right",
    TITLE_CHANGED: "mdi-pencil",
    DESCRIPTION_CHANGED: "mdi-text",
    PRIORITY_CHANGED: "mdi-flag",
    COMMENT_ADDED: "mdi-comment-plus",
  };
  return icons[action] || "mdi-circle";
}

function historyLabel(action) {
  const labels = {
    CREATED: "создал заявку",
    STATUS_CHANGED: "изменил статус",
    ASSIGNEE_CHANGED: "изменил исполнителя",
    TITLE_CHANGED: "изменил название",
    DESCRIPTION_CHANGED: "изменил описание",
    PRIORITY_CHANGED: "изменил приоритет",
    COMMENT_ADDED: "добавил комментарий",
  };
  return labels[action] || action;
}

// Таймер
function startTimer() {
  stopTimer();
  currentTime.value = Date.now();
  timerInterval.value = setInterval(() => {
    currentTime.value = Date.now();
  }, 1000);
}

function stopTimer() {
  if (timerInterval.value) {
    clearInterval(timerInterval.value);
    timerInterval.value = null;
  }
}

watch(
  cur,
  (newCur) => {
    if (newCur && newCur.status === "in_progress") {
      startTimer();
    } else {
      stopTimer();
    }
  },
  { immediate: true },
);

onUnmounted(() => stopTimer());

// Загрузка
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
    if (e.response?.status === 401) logout();
  }
});

watch(viewMode, () => {
  cur.value = null;
  loadTickets();
});

async function loadTickets() {
  try {
    let url = viewMode.value === "my" ? "/tickets/my" : "/tickets";
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
    notify("Ошибка загрузки", "error");
  }
}

let searchTimeout = null;
function debouncedSearch() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => loadTickets(), 300);
}

async function selectTicket(t) {
  try {
    const r = await api.get("/tickets/" + t.key);
    cur.value = { ...r.data, assignee_id: r.data.assignee?.id };
    await loadComments();
    await loadHistory();
  } catch (e) {
    notify("Ошибка загрузки", "error");
  }
}

async function loadComments() {
  if (!cur.value) return;
  try {
    const r = await api.get(`/tickets/${cur.value.key}/comments`);
    comments.value = r.data;
  } catch (e) {
    comments.value = [];
  }
}

async function loadHistory() {
  if (!cur.value) return;
  try {
    const r = await api.get(`/tickets/${cur.value.key}/history`);
    history.value = r.data;
  } catch (e) {
    history.value = [];
  }
}

// Действия
async function startWork() {
  actionLoading.value = true;
  try {
    const r = await api.post("/tickets/" + cur.value.key + "/start");
    cur.value = { ...r.data, assignee_id: r.data.assignee?.id };
    notify("Заявка взята в работу!");
    await loadTickets();
    await loadHistory();
  } catch (e) {
    notify(e.response?.data?.detail || "Ошибка", "error");
  } finally {
    actionLoading.value = false;
  }
}

async function resolveTicket() {
  actionLoading.value = true;
  try {
    const r = await api.post("/tickets/" + cur.value.key + "/resolve");
    cur.value = { ...r.data, assignee_id: r.data.assignee?.id };
    notify("Заявка выполнена!");
    await loadTickets();
    await loadHistory();
  } catch (e) {
    notify(e.response?.data?.detail || "Ошибка", "error");
  } finally {
    actionLoading.value = false;
  }
}

async function reopenTicket() {
  actionLoading.value = true;
  try {
    const r = await api.post("/tickets/" + cur.value.key + "/reopen");
    cur.value = { ...r.data, assignee_id: r.data.assignee?.id };
    notify("Заявка возвращена в работу!");
    await loadTickets();
    await loadHistory();
  } catch (e) {
    notify(e.response?.data?.detail || "Ошибка", "error");
  } finally {
    actionLoading.value = false;
  }
}

async function updateField(field, value) {
  try {
    await api.patch("/tickets/" + cur.value.key, { [field]: value });
    notify("Сохранено");
    await loadTickets();
    await loadHistory();
  } catch (e) {
    notify("Ошибка", "error");
  }
}

// Редактирование
function openEditTitle() {
  editTitle.value = cur.value.title;
  showEditTitle.value = true;
}
async function saveTitle() {
  await updateField("title", editTitle.value);
  cur.value.title = editTitle.value;
  showEditTitle.value = false;
}

function openEditDescription() {
  editDescription.value = cur.value.description || "";
  showEditDescription.value = true;
}
async function saveDescription() {
  await updateField("description", editDescription.value);
  cur.value.description = editDescription.value;
  showEditDescription.value = false;
}

function openTransfer() {
  transferUserId.value = null;
  showTransfer.value = true;
}
async function transferTicket() {
  await updateField("assignee_id", transferUserId.value);
  showTransfer.value = false;
  await selectTicket(cur.value);
}

// Комментарии
function formatText(type) {
  const formats = {
    bold: { prefix: "<b>", suffix: "</b>" },
    italic: { prefix: "<i>", suffix: "</i>" },
    underline: { prefix: "<u>", suffix: "</u>" },
    h2: { prefix: "<h3>", suffix: "</h3>" },
    ul: { prefix: "<ul><li>", suffix: "</li></ul>" },
    code: { prefix: "<code>", suffix: "</code>" },
  };
  const f = formats[type];
  if (f) newComment.value += f.prefix + "текст" + f.suffix;
}

async function addComment() {
  if (!newComment.value.trim()) return;
  try {
    await api.post(`/tickets/${cur.value.key}/comments`, {
      content: newComment.value,
    });
    newComment.value = "";
    await loadComments();
    await loadHistory();
    notify("Комментарий добавлен");
  } catch (e) {
    notify("Ошибка", "error");
  }
}

function editComment(comment) {
  editingCommentId.value = comment.id;
  editCommentContent.value = comment.content;
  showEditComment.value = true;
}

async function saveComment() {
  try {
    await api.put(
      `/tickets/${cur.value.key}/comments/${editingCommentId.value}`,
      { content: editCommentContent.value },
    );
    showEditComment.value = false;
    await loadComments();
    notify("Комментарий обновлён");
  } catch (e) {
    notify("Ошибка", "error");
  }
}

async function deleteComment(comment) {
  if (!confirm("Удалить комментарий?")) return;
  try {
    await api.delete(`/tickets/${cur.value.key}/comments/${comment.id}`);
    await loadComments();
    notify("Комментарий удалён");
  } catch (e) {
    notify("Ошибка", "error");
  }
}

// Создание заявки
async function openCreate() {
  const r = await api.get("/tickets/roles");
  roles.value = r.data;
  if (roles.value.length) newTicket.value.role_id = roles.value[0].id;
  newTicket.value = {
    title: "",
    description: "",
    priority: "medium",
    role_id: roles.value[0]?.id,
    assignee_id: null,
  };
  showCreate.value = true;
}

async function createTicket() {
  try {
    const result = await api.post("/tickets", newTicket.value);
    showCreate.value = false;
    notify(`Заявка ${result.data.key} создана!`);
    await loadTickets();
    await selectTicket(result.data);
  } catch (e) {
    notify(e.response?.data?.detail || "Ошибка", "error");
  }
}

// Админ
async function openAdmin() {
  showAdmin.value = true;
  const r = await api.get("/users");
  allUsers.value = r.data.map((u) => ({ ...u, newRoleId: u.role.id }));
}

async function changeRole(u) {
  try {
    await api.patch("/users/" + u.id + "/role", { role_id: u.newRoleId });
    notify("Роль изменена");
    await openAdmin();
  } catch (e) {
    notify("Ошибка", "error");
  }
}

async function toggleUserStatus(u) {
  try {
    await api.patch("/users/" + u.id + "/status", { is_active: !u.is_active });
    notify("Статус изменён");
    await openAdmin();
  } catch (e) {
    notify("Ошибка", "error");
  }
}

function logout() {
  authStore.logout();
  router.push("/login");
}
</script>

<style>
.comment-content {
  line-height: 1.6;
}
.comment-content h3 {
  font-size: 1.1em;
  margin: 0.5em 0;
}
.comment-content code {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}
.comment-content ul {
  margin: 0.5em 0;
  padding-left: 1.5em;
}
</style>

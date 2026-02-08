<template>
  <v-app :theme="isDark ? 'dark' : 'light'">
    <!-- Шапка -->
    <v-app-bar color="primary" density="compact">
      <!-- КРАСИВЫЙ ЛОГОТИП -->
      <div class="logo-container" @click="goHome">
        <div class="logo-icon">
          <v-icon color="white" size="24">mdi-ticket-confirmation</v-icon>
        </div>
        <div class="logo-text">
          <span class="logo-main">Gerask</span>
          <span class="logo-sub">Task Manager</span>
        </div>
      </div>

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

      <!-- Колокольчик уведомлений -->
      <v-menu offset-y :close-on-content-click="false">
        <template v-slot:activator="{ props }">
          <v-btn icon v-bind="props" class="mr-2">
            <v-badge
              :content="unreadCount"
              :model-value="unreadCount > 0"
              color="error"
            >
              <v-icon>mdi-bell</v-icon>
            </v-badge>
          </v-btn>
        </template>
        <v-card width="400">
          <v-card-title class="d-flex align-center py-2">
            <span>Уведомления</span>
            <v-spacer></v-spacer>
            <v-btn
              size="small"
              variant="text"
              @click="markAllRead"
              v-if="notifications.length"
            >
              Прочитать все
            </v-btn>
          </v-card-title>
          <v-divider></v-divider>
          <v-list
            v-if="notifications.length"
            density="compact"
            max-height="400"
            class="overflow-y-auto"
          >
            <v-list-item
              v-for="n in notifications"
              :key="n.id"
              :class="{ 'bg-blue-lighten-5': !n.is_read }"
              @click="openNotification(n)"
            >
              <template v-slot:prepend>
                <v-icon :color="n.is_read ? 'grey' : 'primary'" size="small">
                  {{ n.type === "MENTION" ? "mdi-at" : "mdi-bell" }}
                </v-icon>
              </template>
              <v-list-item-title class="text-body-2">{{
                n.message
              }}</v-list-item-title>
              <v-list-item-subtitle class="text-caption">{{
                formatDate(n.created_at)
              }}</v-list-item-subtitle>
            </v-list-item>
          </v-list>
          <v-card-text v-else class="text-center text-grey py-4"
            >Нет уведомлений</v-card-text
          >
        </v-card>
      </v-menu>

      <!-- Переключатель темы -->
      <v-btn
        icon
        @click="toggleTheme"
        class="mr-1"
        :title="isDark ? 'Светлая тема' : 'Тёмная тема'"
      >
        <v-icon>{{
          isDark ? "mdi-weather-sunny" : "mdi-weather-night"
        }}</v-icon>
      </v-btn>

      <v-btn v-if="isAdmin" variant="text" @click="openAdmin">
        <v-icon>mdi-account-cog</v-icon>
      </v-btn>
      <v-btn icon @click="logout">
        <v-icon>mdi-logout</v-icon>
      </v-btn>
    </v-app-bar>

    <v-main class="main-content">
      <div class="layout-container">
        <!-- ЛЕВАЯ ПАНЕЛЬ -->
        <div class="left-panel">
          <v-card class="h-100">
            <v-card-title class="d-flex align-center py-2">
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
            <v-card-text v-if="viewMode === 'all'" class="pb-0 pt-0">
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
              class="tickets-list"
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
                <v-list-item-title class="font-weight-bold text-truncate">{{
                  t.key
                }}</v-list-item-title>
                <v-list-item-subtitle class="text-truncate">{{
                  t.title
                }}</v-list-item-subtitle>
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
        </div>

        <!-- ПРАВАЯ ПАНЕЛЬ -->
        <div class="right-panel">
          <v-alert v-if="isReader" type="info" class="mb-4">
            Вы читатель. Обратитесь к администратору для получения роли.
          </v-alert>

          <v-card v-if="cur">
            <!-- Заголовок -->
            <v-card-title class="d-flex align-center">
              <v-chip
                :color="cur.role?.prefix ? 'primary' : 'grey'"
                class="mr-2"
                >{{ cur.key }}</v-chip
              >
              <span class="flex-grow-1">{{ cur.title }}</span>

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
                      ><v-icon start>mdi-account-arrow-right</v-icon>
                      Передать</v-list-item-title
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

                <v-col
                  cols="auto"
                  v-if="
                    cur.status === 'in_progress' ||
                    cur.status === 'waiting' ||
                    cur.time_spent > 0
                  "
                >
                  <v-chip
                    :color="cur.status === 'waiting' ? 'info' : 'blue-grey'"
                    variant="outlined"
                    size="large"
                  >
                    <v-icon start>{{
                      cur.status === "waiting" ? "mdi-pause" : "mdi-timer"
                    }}</v-icon>
                    {{ liveTimer }}
                    <span
                      v-if="cur.status === 'waiting'"
                      class="ml-1 text-caption"
                      >(пауза)</span
                    >
                  </v-chip>
                </v-col>

                <v-spacer></v-spacer>

                <v-col cols="auto" v-if="isAssignee">
                  <v-btn
                    v-if="cur.status === 'open'"
                    color="primary"
                    @click="startWork"
                    :loading="actionLoading"
                  >
                    <v-icon start>mdi-play</v-icon> Взять в работу
                  </v-btn>

                  <template v-if="cur.status === 'in_progress'">
                    <v-btn
                      color="info"
                      class="mr-2"
                      @click="pauseTicket"
                      :loading="actionLoading"
                    >
                      <v-icon start>mdi-pause</v-icon> Ожидание
                    </v-btn>
                    <v-btn
                      color="success"
                      @click="resolveTicket"
                      :loading="actionLoading"
                    >
                      <v-icon start>mdi-check</v-icon> Решение запроса
                    </v-btn>
                  </template>

                  <v-btn
                    v-if="cur.status === 'waiting'"
                    color="primary"
                    @click="resumeTicket"
                    :loading="actionLoading"
                  >
                    <v-icon start>mdi-play</v-icon> Возобновить
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
                    @update:model-value="updateField('priority', cur.priority)"
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
                class="text-body-1 pa-3 rounded description-content"
                :class="isDark ? 'bg-grey-darken-3' : 'bg-grey-lighten-4'"
                style="min-height: 60px"
                v-html="formatDescription(cur.description)"
              ></div>

              <v-divider class="my-4"></v-divider>

              <!-- Метаданные -->
              <v-row class="text-caption">
                <v-col cols="3">
                  <span class="text-grey">Создано:</span><br />{{
                    formatDate(cur.created_at)
                  }}
                </v-col>
                <v-col cols="3">
                  <span class="text-grey">Решено:</span><br />{{
                    cur.resolved_at ? formatDate(cur.resolved_at) : "-"
                  }}
                </v-col>
                <v-col cols="3">
                  <span class="text-grey">Время в работе:</span><br />{{
                    formatTimeSpent(cur.time_spent)
                  }}
                </v-col>
                <v-col cols="3">
                  <span class="text-grey">Дедлайн:</span><br />{{
                    cur.deadline ? formatDate(cur.deadline) : "-"
                  }}
                </v-col>
              </v-row>

              <v-divider class="my-4"></v-divider>

              <!-- ВКЛАДКИ -->
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
                <!-- КОММЕНТАРИИ -->
                <v-window-item value="comments">
                  <!-- Скрытые комментарии -->
                  <div v-if="hiddenComments.length > 0" class="mb-4">
                    <v-btn
                      variant="outlined"
                      color="grey"
                      block
                      @click="showAllComments = !showAllComments"
                    >
                      <v-icon start>{{
                        showAllComments ? "mdi-chevron-up" : "mdi-chevron-down"
                      }}</v-icon>
                      {{ showAllComments ? "Скрыть" : "Показать" }} ранние
                      комментарии ({{ hiddenComments.length }})
                    </v-btn>

                    <v-expand-transition>
                      <div v-show="showAllComments" class="mt-3">
                        <v-card
                          v-for="comment in hiddenComments"
                          :key="comment.id"
                          variant="outlined"
                          class="mb-2"
                          :class="
                            isDark ? 'bg-grey-darken-3' : 'bg-grey-lighten-5'
                          "
                        >
                          <v-card-text class="py-2">
                            <div class="d-flex align-center mb-2">
                              <v-avatar size="32" color="grey" class="mr-2">
                                <span class="text-white text-caption">{{
                                  comment.author?.display_name?.charAt(0) || "?"
                                }}</span>
                              </v-avatar>
                              <div>
                                <strong>{{
                                  comment.author?.display_name
                                }}</strong>
                                <div class="text-caption text-grey">
                                  {{ formatDate(comment.created_at) }}
                                </div>
                              </div>
                              <v-spacer></v-spacer>
                              <v-btn
                                v-if="
                                  comment.author?.id === user?.id || isAdmin
                                "
                                icon
                                size="x-small"
                                variant="text"
                                @click="editComment(comment)"
                              >
                                <v-icon size="small">mdi-pencil</v-icon>
                              </v-btn>
                              <v-btn
                                v-if="
                                  comment.author?.id === user?.id || isAdmin
                                "
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
                              v-html="renderCommentContent(comment.content)"
                              class="comment-content"
                            ></div>
                          </v-card-text>
                        </v-card>
                      </div>
                    </v-expand-transition>
                  </div>

                  <!-- Видимые комментарии -->
                  <div v-if="visibleComments.length">
                    <v-card
                      v-for="comment in visibleComments"
                      :key="comment.id"
                      variant="outlined"
                      class="mb-3"
                    >
                      <v-card-text class="py-2">
                        <div class="d-flex align-center mb-2">
                          <v-avatar size="32" color="primary" class="mr-2">
                            <span class="text-white text-caption">{{
                              comment.author?.display_name?.charAt(0) || "?"
                            }}</span>
                          </v-avatar>
                          <div>
                            <strong>{{ comment.author?.display_name }}</strong>
                            <div class="text-caption text-grey">
                              {{ formatDate(comment.created_at) }}
                              <span
                                v-if="comment.updated_at !== comment.created_at"
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
                          v-html="renderCommentContent(comment.content)"
                          class="comment-content"
                        ></div>
                      </v-card-text>
                    </v-card>
                  </div>
                  <div v-else class="text-center text-grey py-4">
                    Комментариев пока нет
                  </div>

                  <!-- Форма комментария -->
                  <v-card
                    variant="outlined"
                    v-if="canEdit"
                    class="mt-4 comment-form-card"
                  >
                    <v-card-text>
                      <div class="d-flex gap-2 mb-2 flex-wrap align-center">
                        <v-btn
                          size="x-small"
                          variant="text"
                          @click="formatText('bold')"
                          title="Жирный"
                        >
                          <v-icon>mdi-format-bold</v-icon>
                        </v-btn>
                        <v-btn
                          size="x-small"
                          variant="text"
                          @click="formatText('italic')"
                          title="Курсив"
                        >
                          <v-icon>mdi-format-italic</v-icon>
                        </v-btn>
                        <v-btn
                          size="x-small"
                          variant="text"
                          @click="formatText('code')"
                          title="Код"
                        >
                          <v-icon>mdi-code-tags</v-icon>
                        </v-btn>
                        <v-divider vertical class="mx-2"></v-divider>
                        <v-btn
                          size="x-small"
                          variant="text"
                          @click="triggerFileUpload"
                          title="Прикрепить"
                        >
                          <v-icon>mdi-image-plus</v-icon>
                        </v-btn>
                        <input
                          ref="fileInput"
                          type="file"
                          accept="image/*,.pdf,.doc,.docx,.xls,.xlsx"
                          style="display: none"
                          @change="uploadFile"
                        />
                        <v-spacer></v-spacer>

                        <v-btn-toggle
                          v-model="editorMode"
                          density="compact"
                          mandatory
                          class="mr-2"
                        >
                          <v-btn value="edit" size="x-small" title="Редактор"
                            ><v-icon size="small">mdi-pencil</v-icon></v-btn
                          >
                          <v-btn value="preview" size="x-small" title="Превью"
                            ><v-icon size="small">mdi-eye</v-icon></v-btn
                          >
                        </v-btn-toggle>

                        <v-btn-toggle
                          v-model="textareaSize"
                          density="compact"
                          mandatory
                        >
                          <v-btn value="small" size="x-small"
                            ><v-icon size="small"
                              >mdi-unfold-less-horizontal</v-icon
                            ></v-btn
                          >
                          <v-btn value="medium" size="x-small"
                            ><v-icon size="small">mdi-minus</v-icon></v-btn
                          >
                          <v-btn value="large" size="x-small"
                            ><v-icon size="small"
                              >mdi-unfold-more-horizontal</v-icon
                            ></v-btn
                          >
                        </v-btn-toggle>
                      </div>

                      <!-- Редактирование -->
                      <div
                        v-show="editorMode === 'edit'"
                        class="mention-container"
                      >
                        <v-card
                          v-if="showMentionList && filteredMentionUsers.length"
                          class="mention-dropdown elevation-8"
                        >
                          <v-list density="compact" class="py-0">
                            <v-list-item
                              v-for="(u, index) in filteredMentionUsers"
                              :key="u.id"
                              :class="{ 'bg-primary': mentionIndex === index }"
                              @click="insertMention(u)"
                              @mouseenter="mentionIndex = index"
                            >
                              <template v-slot:prepend>
                                <v-avatar size="28" color="grey-lighten-2">
                                  <span class="text-caption">{{
                                    u.display_name?.charAt(0)
                                  }}</span>
                                </v-avatar>
                              </template>
                              <v-list-item-title
                                :class="{
                                  'text-white': mentionIndex === index,
                                }"
                                >{{ u.display_name }}</v-list-item-title
                              >
                              <v-list-item-subtitle
                                :class="{
                                  'text-white': mentionIndex === index,
                                }"
                                >@{{ u.login }}</v-list-item-subtitle
                              >
                            </v-list-item>
                          </v-list>
                        </v-card>

                        <v-textarea
                          ref="commentInput"
                          v-model="newComment"
                          :label="
                            'Комментарий... (@ для упоминания' +
                            (mentionSearchText
                              ? ': ' + mentionSearchText
                              : '') +
                            ')'
                          "
                          :rows="textareaRows"
                          hide-details
                          variant="outlined"
                          auto-grow
                          @input="handleInput"
                          @keydown="handleKeydown"
                          @blur="hideMentionListDelayed"
                        ></v-textarea>
                      </div>

                      <!-- Превью -->
                      <div
                        v-show="editorMode === 'preview'"
                        class="preview-container pa-3 rounded"
                        :style="{ minHeight: previewMinHeight + 'px' }"
                      >
                        <div
                          v-if="newComment.trim()"
                          v-html="renderPreview(newComment)"
                          class="comment-content"
                        ></div>
                        <div v-else class="text-grey text-center py-4">
                          <v-icon>mdi-eye-off</v-icon>
                          <div class="text-caption mt-1">
                            Нет контента для превью
                          </div>
                        </div>
                      </div>

                      <div
                        v-if="uploadedFiles.length"
                        class="d-flex gap-2 mt-2 flex-wrap"
                      >
                        <v-chip
                          v-for="file in uploadedFiles"
                          :key="file.id"
                          closable
                          @click:close="removeUploadedFile(file)"
                        >
                          <v-icon start size="small">mdi-paperclip</v-icon
                          >{{ file.filename }}
                        </v-chip>
                      </div>

                      <div class="d-flex justify-end mt-2">
                        <v-btn
                          color="primary"
                          @click="addComment"
                          :disabled="
                            !newComment.trim() && !uploadedFiles.length
                          "
                          :loading="commentLoading"
                        >
                          <v-icon start>mdi-send</v-icon> Отправить
                        </v-btn>
                      </div>
                    </v-card-text>
                  </v-card>
                </v-window-item>

                <!-- История -->
                <v-window-item value="history">
                  <div v-if="history.length">
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
                            >{{ historyIcon(item.action) }}</v-icon
                          >
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

          <v-card v-else>
            <v-card-text class="text-center text-grey py-16">
              <v-icon size="80" color="grey-lighten-1"
                >mdi-ticket-outline</v-icon
              >
              <div class="text-h6 mt-4">Выберите заявку из списка</div>
            </v-card-text>
          </v-card>
        </div>
      </div>
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

    <v-dialog v-model="showImageViewer" max-width="95vw" max-height="95vh">
      <v-card
        class="bg-black d-flex align-center justify-center"
        style="min-height: 80vh"
      >
        <v-btn
          icon
          variant="text"
          color="white"
          class="position-absolute"
          style="top: 8px; right: 8px; z-index: 10"
          @click="showImageViewer = false"
        >
          <v-icon size="large">mdi-close</v-icon>
        </v-btn>
        <img
          :src="viewerImageSrc"
          style="max-width: 100%; max-height: 90vh; object-fit: contain"
          @click="showImageViewer = false"
        />
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :color="snackbarColor" timeout="3000">{{
      snackbarText
    }}</v-snackbar>
  </v-app>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "../stores/auth";
import api from "../api";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

// Тема
const isDark = ref(localStorage.getItem("theme") === "dark");

function toggleTheme() {
  isDark.value = !isDark.value;
  localStorage.setItem("theme", isDark.value ? "dark" : "light");
}

// Состояние
const user = ref(null);
const viewMode = ref("my");
const actionLoading = ref(false);
const commentLoading = ref(false);
const activeTab = ref("comments");
const showAllComments = ref(false);
const editorMode = ref("edit");
const textareaSize = ref("medium");

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
const showImageViewer = ref(false);

// Формы
const editTitle = ref("");
const editDescription = ref("");
const transferUserId = ref(null);
const newComment = ref("");
const editCommentContent = ref("");
const editingCommentId = ref(null);
const viewerImageSrc = ref("");
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
const timerTick = ref(0);

// @Mentions
const showMentionList = ref(false);
const mentionIndex = ref(0);
const mentionStart = ref(0);
const mentionSearchText = ref("");

// Файлы
const fileInput = ref(null);
const uploadedFiles = ref([]);

// Уведомления
const notifications = ref([]);
const unreadCount = ref(0);

// Опции
const statusFilterOptions = [
  { title: "Все", value: null },
  { title: "Открыта", value: "open" },
  { title: "В работе", value: "in_progress" },
  { title: "Ожидание", value: "waiting" },
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

// Computed
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

const textareaRows = computed(
  () => ({ small: 2, medium: 4, large: 8 })[textareaSize.value] || 4,
);
const previewMinHeight = computed(
  () => ({ small: 60, medium: 120, large: 200 })[textareaSize.value] || 120,
);

const visibleComments = computed(() =>
  comments.value.length <= 5 ? comments.value : comments.value.slice(-5),
);
const hiddenComments = computed(() =>
  comments.value.length <= 5 ? [] : comments.value.slice(0, -5),
);

const filteredMentionUsers = computed(() => {
  const search = mentionSearchText.value.toLowerCase();
  return users.value
    .filter(
      (u) =>
        !search ||
        u.display_name?.toLowerCase().includes(search) ||
        u.login?.toLowerCase().includes(search),
    )
    .slice(0, 8);
});

const liveTimer = computed(() => {
  const _ = timerTick.value;
  if (!cur.value) return "00:00:00";
  let totalSeconds = cur.value.time_spent || 0;
  if (cur.value.status === "in_progress" && cur.value.timer_started_at) {
    const timerStartedStr = cur.value.timer_started_at;
    let timerStarted =
      timerStartedStr.endsWith("Z") || timerStartedStr.includes("+")
        ? new Date(timerStartedStr)
        : new Date(timerStartedStr + "Z");
    totalSeconds += Math.max(
      0,
      Math.floor((new Date().getTime() - timerStarted.getTime()) / 1000),
    );
  }
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
});

// Функции
function notify(text, color = "success") {
  snackbarText.value = text;
  snackbarColor.value = color;
  snackbar.value = true;
}
function formatDate(dateStr) {
  return dateStr ? new Date(dateStr).toLocaleString("ru-RU") : "-";
}
function formatTimeSpent(seconds) {
  if (!seconds) return "0 сек";
  const h = Math.floor(seconds / 3600),
    m = Math.floor((seconds % 3600) / 60),
    s = seconds % 60;
  return h > 0 ? `${h} ч ${m} мин` : m > 0 ? `${m} мин ${s} сек` : `${s} сек`;
}
function formatDescription(text) {
  return text
    ? text.replace(/\n/g, "<br>")
    : '<span class="text-grey">Нет описания</span>';
}
function statusColor(s) {
  return (
    {
      open: "grey",
      in_progress: "warning",
      waiting: "info",
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
      waiting: "Ожидание",
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
function historyColor(a) {
  return (
    {
      CREATED: "primary",
      STATUS_CHANGED: "warning",
      ASSIGNEE_CHANGED: "info",
      TITLE_CHANGED: "secondary",
      DESCRIPTION_CHANGED: "secondary",
      PRIORITY_CHANGED: "orange",
      COMMENT_ADDED: "success",
    }[a] || "grey"
  );
}
function historyIcon(a) {
  return (
    {
      CREATED: "mdi-plus-circle",
      STATUS_CHANGED: "mdi-swap-horizontal",
      ASSIGNEE_CHANGED: "mdi-account-arrow-right",
      TITLE_CHANGED: "mdi-pencil",
      DESCRIPTION_CHANGED: "mdi-text",
      PRIORITY_CHANGED: "mdi-flag",
      COMMENT_ADDED: "mdi-comment-plus",
    }[a] || "mdi-circle"
  );
}
function historyLabel(a) {
  return (
    {
      CREATED: "создал заявку",
      STATUS_CHANGED: "изменил статус",
      ASSIGNEE_CHANGED: "изменил исполнителя",
      TITLE_CHANGED: "изменил название",
      DESCRIPTION_CHANGED: "изменил описание",
      PRIORITY_CHANGED: "изменил приоритет",
      COMMENT_ADDED: "добавил комментарий",
    }[a] || a
  );
}

function renderCommentContent(content) {
  if (!content) return "";
  let result = content
    .replace(/\n/g, "<br>")
    .replace(/@\[([^\]]+)\]/g, '<span class="mention-tag">@$1</span>');
  result = result.replace(
    /<img\s+src="([^"]+)"[^>]*>/gi,
    (m, src) =>
      `<span class="thumbnail-wrapper" onclick="window.openImageViewer('${src}')"><img src="${src}" class="thumbnail-img" alt=""><span class="thumbnail-overlay"><span class="thumbnail-icon">🔍</span></span></span>`,
  );
  return result;
}

function renderPreview(content) {
  if (!content) return "";
  let result = content
    .replace(/\n/g, "<br>")
    .replace(/@\[([^\]]+)\]/g, '<span class="mention-tag">@$1</span>');
  result = result.replace(
    /<img\s+src="([^"]+)"[^>]*>/gi,
    (m, src) =>
      `<div class="preview-image-container"><img src="${src}" class="preview-image" alt=""></div>`,
  );
  return result;
}

if (typeof window !== "undefined") {
  window.openImageViewer = (src) => {
    viewerImageSrc.value = src;
    showImageViewer.value = true;
  };
}

// Таймер
function startTimer() {
  stopTimer();
  timerInterval.value = setInterval(() => timerTick.value++, 1000);
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
    if (newCur?.status === "in_progress") startTimer();
    else stopTimer();
    showAllComments.value = false;
  },
  { immediate: true },
);

onUnmounted(() => stopTimer());

// Навигация
function goHome() {
  cur.value = null;
  router.push("/");
}

// Загрузка заявки из URL
async function loadTicketFromUrl() {
  const ticketKey = route.params.key;
  if (ticketKey) {
    try {
      const r = await api.get("/tickets/" + ticketKey);
      cur.value = { ...r.data, assignee_id: r.data.assignee?.id };
      await loadComments();
      await loadHistory();
    } catch (e) {
      router.push("/");
      notify("Заявка не найдена", "error");
    }
  }
}

onMounted(async () => {
  try {
    const r = await api.get("/auth/me");
    user.value = r.data;
    authStore.user = r.data;
    users.value = (await api.get("/tickets/users")).data;
    allRoles.value = (await api.get("/users/roles")).data;
    await loadTickets();
    await loadNotifications();
    await loadTicketFromUrl();
    setInterval(loadNotifications, 30000);
  } catch (e) {
    if (e.response?.status === 401) logout();
  }
});

watch(
  () => route.params.key,
  async (newKey) => {
    if (newKey) await loadTicketFromUrl();
    else if (route.path === "/") cur.value = null;
  },
);

watch(viewMode, () => {
  cur.value = null;
  if (route.params.key) router.push("/");
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
    tickets.value = (await api.get(url)).data;
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
    router.push({ name: "Ticket", params: { key: t.key } });
    await loadComments();
    await loadHistory();
  } catch (e) {
    notify("Ошибка загрузки", "error");
  }
}

async function loadComments() {
  if (cur.value)
    comments.value = (
      await api
        .get(`/tickets/${cur.value.key}/comments`)
        .catch(() => ({ data: [] }))
    ).data;
}
async function loadHistory() {
  if (cur.value)
    history.value = (
      await api
        .get(`/tickets/${cur.value.key}/history`)
        .catch(() => ({ data: [] }))
    ).data;
}
async function loadNotifications() {
  try {
    notifications.value = (await api.get("/tickets/notifications")).data;
    unreadCount.value = (
      await api.get("/tickets/notifications/unread/count")
    ).data.count;
  } catch (e) {}
}
async function markAllRead() {
  await api.post("/tickets/notifications/read-all");
  await loadNotifications();
}
async function openNotification(n) {
  if (!n.is_read) await api.post(`/tickets/notifications/${n.id}/read`);
  if (n.ticket_id) {
    const ticket = (await api.get("/tickets")).data.find(
      (t) => t.id === n.ticket_id,
    );
    if (ticket) await selectTicket(ticket);
  }
  await loadNotifications();
}

async function startWork() {
  actionLoading.value = true;
  try {
    cur.value = {
      ...(await api.post("/tickets/" + cur.value.key + "/start")).data,
      assignee_id: cur.value.assignee_id,
    };
    notify("Заявка взята в работу!");
    await loadTickets();
    await loadHistory();
  } catch (e) {
    notify(e.response?.data?.detail || "Ошибка", "error");
  } finally {
    actionLoading.value = false;
  }
}

async function pauseTicket() {
  actionLoading.value = true;
  try {
    cur.value = {
      ...(await api.post("/tickets/" + cur.value.key + "/pause")).data,
      assignee_id: cur.value.assignee_id,
    };
    notify("Заявка приостановлена");
    await loadTickets();
    await loadHistory();
  } catch (e) {
    notify(e.response?.data?.detail || "Ошибка", "error");
  } finally {
    actionLoading.value = false;
  }
}

async function resumeTicket() {
  actionLoading.value = true;
  try {
    cur.value = {
      ...(await api.post("/tickets/" + cur.value.key + "/resume")).data,
      assignee_id: cur.value.assignee_id,
    };
    notify("Работа возобновлена!");
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
    cur.value = {
      ...(await api.post("/tickets/" + cur.value.key + "/resolve")).data,
      assignee_id: cur.value.assignee_id,
    };
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
    cur.value = {
      ...(await api.post("/tickets/" + cur.value.key + "/reopen")).data,
      assignee_id: cur.value.assignee_id,
    };
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

function formatText(type) {
  const f = {
    bold: { prefix: "<b>", suffix: "</b>" },
    italic: { prefix: "<i>", suffix: "</i>" },
    code: { prefix: "<code>", suffix: "</code>" },
  }[type];
  if (f) newComment.value += f.prefix + "текст" + f.suffix;
}

function handleInput(event) {
  const text = newComment.value,
    cursorPos = event.target.selectionStart,
    beforeCursor = text.substring(0, cursorPos),
    atIndex = beforeCursor.lastIndexOf("@");
  if (atIndex !== -1) {
    const afterAt = beforeCursor.substring(atIndex);
    if (!afterAt.includes("]")) {
      const searchText = afterAt.substring(1);
      if (!searchText.includes(" ") && !searchText.includes("\n")) {
        mentionStart.value = atIndex;
        mentionSearchText.value = searchText;
        showMentionList.value = true;
        mentionIndex.value = 0;
        return;
      }
    }
  }
  showMentionList.value = false;
  mentionSearchText.value = "";
}

function handleKeydown(event) {
  if (!showMentionList.value || !filteredMentionUsers.value.length) return;
  if (event.key === "ArrowDown") {
    event.preventDefault();
    mentionIndex.value =
      (mentionIndex.value + 1) % filteredMentionUsers.value.length;
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    mentionIndex.value =
      (mentionIndex.value - 1 + filteredMentionUsers.value.length) %
      filteredMentionUsers.value.length;
  } else if (event.key === "Enter" || event.key === "Tab") {
    event.preventDefault();
    insertMention(filteredMentionUsers.value[mentionIndex.value]);
  } else if (event.key === "Escape") showMentionList.value = false;
}

function insertMention(u) {
  newComment.value =
    newComment.value.substring(0, mentionStart.value) +
    `@[${u.display_name}]` +
    newComment.value.substring(
      mentionStart.value + 1 + mentionSearchText.value.length,
    );
  showMentionList.value = false;
  mentionSearchText.value = "";
}

function hideMentionListDelayed() {
  setTimeout(() => (showMentionList.value = false), 200);
}

async function addComment() {
  if (!newComment.value.trim() && !uploadedFiles.value.length) return;
  commentLoading.value = true;
  try {
    await api.post(`/tickets/${cur.value.key}/comments`, {
      content: newComment.value,
    });
    newComment.value = "";
    uploadedFiles.value = [];
    editorMode.value = "edit";
    await loadComments();
    await loadHistory();
    notify("Комментарий добавлен");
  } catch (e) {
    notify("Ошибка", "error");
  } finally {
    commentLoading.value = false;
  }
}

function editComment(c) {
  editingCommentId.value = c.id;
  editCommentContent.value = c.content;
  showEditComment.value = true;
}
async function saveComment() {
  await api.put(
    `/tickets/${cur.value.key}/comments/${editingCommentId.value}`,
    { content: editCommentContent.value },
  );
  showEditComment.value = false;
  await loadComments();
  notify("Комментарий обновлён");
}
async function deleteComment(c) {
  if (!confirm("Удалить комментарий?")) return;
  await api.delete(`/tickets/${cur.value.key}/comments/${c.id}`);
  await loadComments();
  notify("Комментарий удалён");
}

function triggerFileUpload() {
  fileInput.value?.click();
}
async function uploadFile(event) {
  const file = event.target.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append("file", file);
  try {
    const r = await api.post(`/tickets/${cur.value.key}/upload`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    uploadedFiles.value.push(r.data);
    const fileUrl = `http://localhost:8000${r.data.url}`;
    newComment.value += r.data.mime_type?.startsWith("image/")
      ? `\n<img src="${fileUrl}" alt="${r.data.filename}">`
      : `\n<a href="${fileUrl}" target="_blank" class="file-link">📎 ${r.data.filename}</a>`;
    notify("Файл загружен");
  } catch (e) {
    notify(e.response?.data?.detail || "Ошибка загрузки", "error");
  }
  event.target.value = "";
}
function removeUploadedFile(f) {
  uploadedFiles.value = uploadedFiles.value.filter((x) => x.id !== f.id);
}

async function openCreate() {
  roles.value = (await api.get("/tickets/roles")).data;
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

async function openAdmin() {
  showAdmin.value = true;
  allUsers.value = (await api.get("/users")).data.map((u) => ({
    ...u,
    newRoleId: u.role.id,
  }));
}
async function changeRole(u) {
  await api.patch("/users/" + u.id + "/role", { role_id: u.newRoleId });
  notify("Роль изменена");
  await openAdmin();
}
async function toggleUserStatus(u) {
  await api.patch("/users/" + u.id + "/status", { is_active: !u.is_active });
  notify("Статус изменён");
  await openAdmin();
}

function logout() {
  authStore.logout();
  router.push("/login");
}
</script>

<style>
.main-content {
  height: calc(100vh - 48px);
  overflow: hidden;
}
.layout-container {
  display: flex;
  height: 100%;
  padding: 16px;
  gap: 16px;
}
.left-panel {
  width: 350px;
  min-width: 300px;
  max-width: 400px;
  height: 100%;
  flex-shrink: 0;
}
.left-panel .v-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.tickets-list {
  flex: 1;
  overflow-y: auto;
}
.right-panel {
  flex: 1;
  overflow-y: auto;
  padding-right: 8px;
}

.logo-container {
  display: flex;
  align-items: center;
  padding: 0 16px;
  cursor: pointer;
  transition: all 0.3s ease;
}
.logo-container:hover {
  transform: scale(1.02);
}
.logo-icon {
  width: 40px;
  height: 40px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.3),
    rgba(255, 255, 255, 0.1)
  );
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.2);
}
.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.1;
}
.logo-main {
  font-size: 22px;
  font-weight: 700;
  color: white;
  letter-spacing: 1px;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}
.logo-sub {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.7);
  letter-spacing: 2px;
  text-transform: uppercase;
}

.mention-container {
  position: relative;
}
.mention-dropdown {
  position: absolute;
  bottom: 100%;
  left: 0;
  right: 0;
  max-height: 300px;
  overflow-y: auto;
  z-index: 1000;
  margin-bottom: 4px;
  border-radius: 8px;
}
.mention-tag {
  background: linear-gradient(135deg, #e3f2fd, #bbdefb);
  color: #1565c0;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 500;
  font-size: 0.9em;
  border: 1px solid #90caf9;
}
.comment-content {
  line-height: 1.6;
  word-wrap: break-word;
}
.comment-content code {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}
.description-content {
  line-height: 1.6;
  word-wrap: break-word;
}

.thumbnail-wrapper {
  display: inline-block;
  position: relative;
  margin: 8px 8px 8px 0;
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid #e0e0e0;
  transition: all 0.2s ease;
}
.thumbnail-wrapper:hover {
  border-color: #1976d2;
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
.thumbnail-img {
  display: block;
  max-width: 200px;
  max-height: 150px;
  object-fit: cover;
}
.thumbnail-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease;
}
.thumbnail-wrapper:hover .thumbnail-overlay {
  opacity: 1;
}
.thumbnail-icon {
  font-size: 24px;
  color: white;
}

.preview-container {
  background: #fafafa;
  border: 1px solid #e0e0e0;
}
.v-theme--dark .preview-container {
  background: #424242;
  border-color: #616161;
}
.preview-image-container {
  display: block;
  margin: 8px 0;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid #1976d2;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  max-width: fit-content;
}
.preview-image {
  display: block;
  max-width: 100%;
  max-height: 300px;
  object-fit: contain;
}

.file-link {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  background: #f0f0f0;
  border-radius: 16px;
  color: #1976d2;
  text-decoration: none;
  font-size: 0.9em;
  margin: 4px 4px 4px 0;
}
.file-link:hover {
  background: #e3f2fd;
}
.comment-form-card {
  position: relative;
  overflow: visible !important;
}
.comment-form-card .v-card-text {
  overflow: visible !important;
}
</style>

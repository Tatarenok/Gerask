<template>
  <v-app>
    <v-app-bar color="primary">
      <v-app-bar-title>TicketSystem</v-app-bar-title>
      <v-spacer></v-spacer>
      <v-chip color="white" variant="outlined" class="mr-2">{{ user?.display_name }}</v-chip>
      <v-btn color="success" @click="openCreate">+ Создать</v-btn>
      <v-btn icon @click="logout"><v-icon>mdi-logout</v-icon></v-btn>
    </v-app-bar>
    <v-main>
      <v-container fluid>
        <v-row>
          <v-col cols="4">
            <v-card>
              <v-card-title>Заявки ({{ tickets.length }})</v-card-title>
              <v-list density="compact">
                <v-list-item v-for="t in tickets" :key="t.id" @click="sel(t)" :class="{ 'bg-blue-lighten-4': cur && cur.key === t.key }">
                  <template v-slot:prepend>
                    <v-chip size="x-small" :color="statusColor(t.status)">{{ t.status }}</v-chip>
                  </template>
                  <v-list-item-title>{{ t.key }}</v-list-item-title>
                  <v-list-item-subtitle>{{ t.title }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-card>
          </v-col>
          <v-col cols="8">
            <v-card v-if="cur">
              <v-card-title>{{ cur.key }}: {{ cur.title }}</v-card-title>
              <v-card-text>
                <v-row>
                  <v-col cols="4">
                    <v-select v-model="cur.status" :items="statuses" label="Статус" @change="updateStatus" density="compact"></v-select>
                  </v-col>
                  <v-col cols="4">
                    <v-autocomplete v-model="cur.author_id" :items="users" item-title="display_name" item-value="id" label="Автор" @change="updateTicket" density="compact"></v-autocomplete>
                  </v-col>
                  <v-col cols="4">
                    <v-autocomplete v-model="cur.assignee_id" :items="users" item-title="display_name" item-value="id" label="Исполнитель" @change="updateTicket" density="compact" clearable></v-autocomplete>
                  </v-col>
                </v-row>
                <v-chip :color="priorityColor(cur.priority)" class="mr-2">{{ cur.priority }}</v-chip>
                <v-chip>{{ cur.role?.prefix }}</v-chip>
                <v-divider class="my-4"></v-divider>
                <p>{{ cur.description || 'Нет описания' }}</p>
              </v-card-text>
            </v-card>
            <v-card v-else><v-card-text>Выберите заявку</v-card-text></v-card>
          </v-col>
        </v-row>
      </v-container>
    </v-main>
    <v-dialog v-model="showCreate" max-width="500">
      <v-card>
        <v-card-title>Создать заявку</v-card-title>
        <v-card-text>
          <v-select v-model="newRoleId" :items="roles" item-title="display_name" item-value="id" label="Тип"></v-select>
          <v-text-field v-model="newTitle" label="Название"></v-text-field>
          <v-textarea v-model="newDesc" label="Описание" rows="3"></v-textarea>
          <v-select v-model="newPriority" :items="priorities" label="Приоритет"></v-select>
          <v-autocomplete v-model="newAssigneeId" :items="users" item-title="display_name" item-value="id" label="Исполнитель" clearable></v-autocomplete>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="showCreate=false">Отмена</v-btn>
          <v-btn color="primary" @click="createTicket">Создать</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-app>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { useRouter } from "vue-router"
import api from "../api"

const router = useRouter()
const user = ref(null)
const tickets = ref([])
const cur = ref(null)
const roles = ref([])
const users = ref([])
const showCreate = ref(false)
const newTitle = ref("")
const newDesc = ref("")
const newPriority = ref("medium")
const newRoleId = ref(null)
const newAssigneeId = ref(null)
const priorities = ["low", "medium", "high", "critical"]
const statuses = ["open", "in_progress", "waiting", "done", "closed"]

onMounted(async () => {
  const r = await api.get("/auth/me")
  user.value = r.data
  const u = await api.get("/tickets/users")
  users.value = u.data
  await fetchAll()
})

async function fetchAll() {
  const r = await api.get("/tickets")
  tickets.value = r.data
}

async function sel(t) {
  const r = await api.get("/tickets/" + t.key)
  cur.value = {...r.data, author_id: r.data.author?.id, assignee_id: r.data.assignee?.id}
}

async function openCreate() {
  const r = await api.get("/tickets/roles")
  roles.value = r.data
  if (roles.value.length) newRoleId.value = roles.value[0].id
  showCreate.value = true
}

async function createTicket() {
  await api.post("/tickets", {
    title: newTitle.value,
    description: newDesc.value,
    priority: newPriority.value,
    role_id: newRoleId.value,
    assignee_id: newAssigneeId.value
  })
  showCreate.value = false
  newTitle.value = ""
  newDesc.value = ""
  newAssigneeId.value = null
  await fetchAll()
}

async function updateStatus() {
  await api.patch("/tickets/" + cur.value.key + "/status", { status: cur.value.status })
  await fetchAll()
}

async function updateTicket() {
  await api.patch("/tickets/" + cur.value.key, {
    author_id: cur.value.author_id,
    assignee_id: cur.value.assignee_id
  })
  await fetchAll()
}

function statusColor(s) {
  return { open: "grey", in_progress: "blue", waiting: "orange", done: "green", closed: "grey-darken-2" }[s] || "grey"
}

function priorityColor(p) {
  return { low: "green", medium: "yellow-darken-2", high: "orange", critical: "red" }[p] || "grey"
}

function logout() {
  localStorage.removeItem("token")
  router.push("/login")
}
</script>
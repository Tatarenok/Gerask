<template>
  <v-app>
    <v-container class="fill-height" fluid>
      <v-row align="center" justify="center" style="height: 100vh">
        <v-col cols="12" sm="8" md="4">
          <v-card class="elevation-12">
            <v-toolbar color="primary" dark flat>
              <v-toolbar-title
                >🎫
                {{
                  isRegister ? "Регистрация" : "TicketSystem - Вход"
                }}</v-toolbar-title
              >
            </v-toolbar>
            <v-card-text>
              <v-text-field
                v-model="login"
                label="Логин (мин. 3 символа)"
                prepend-icon="mdi-account"
                :error-messages="errors.login"
                @keyup.enter="submit"
              />
              <v-text-field
                v-model="password"
                label="Пароль (мин. 4 символа)"
                prepend-icon="mdi-lock"
                type="password"
                :error-messages="errors.password"
                @keyup.enter="submit"
              />
              <v-text-field
                v-if="isRegister"
                v-model="password2"
                label="Повторите пароль"
                prepend-icon="mdi-lock-check"
                type="password"
                :error-messages="errors.password2"
              />
              <v-text-field
                v-if="isRegister"
                v-model="displayName"
                label="Имя (опционально)"
                prepend-icon="mdi-badge-account"
              />
              <v-alert v-if="error" type="error" class="mt-3">{{
                error
              }}</v-alert>
              <v-alert v-if="success" type="success" class="mt-3">{{
                success
              }}</v-alert>
            </v-card-text>
            <v-card-actions>
              <v-btn variant="text" @click="toggleMode">
                {{
                  isRegister
                    ? "Есть аккаунт? Войти"
                    : "Нет аккаунта? Регистрация"
                }}
              </v-btn>
              <v-spacer></v-spacer>
              <v-btn color="primary" @click="submit" :loading="loading">
                {{ isRegister ? "Зарегистрироваться" : "Войти" }}
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </v-app>
</template>

<script setup>
import { ref, reactive } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import api from "../api";

const router = useRouter();
const authStore = useAuthStore();

const isRegister = ref(false);
const login = ref("");
const password = ref("");
const password2 = ref("");
const displayName = ref("");
const error = ref("");
const success = ref("");
const loading = ref(false);
const errors = reactive({ login: "", password: "", password2: "" });

function clearErrors() {
  error.value = "";
  errors.login = "";
  errors.password = "";
  errors.password2 = "";
}

function toggleMode() {
  isRegister.value = !isRegister.value;
  clearErrors();
  success.value = "";
}

function validate() {
  clearErrors();
  let valid = true;

  if (login.value.length < 3) {
    errors.login = "Минимум 3 символа";
    valid = false;
  }

  if (password.value.length < 4) {
    errors.password = "Минимум 4 символа";
    valid = false;
  }

  if (isRegister.value && password.value !== password2.value) {
    errors.password2 = "Пароли не совпадают";
    valid = false;
  }

  return valid;
}

async function submit() {
  if (!validate()) return;

  loading.value = true;
  error.value = "";

  try {
    if (isRegister.value) {
      // Регистрация
      await api.post("/auth/register", {
        login: login.value,
        password: password.value,
        password_confirm: password2.value,
        display_name: displayName.value || login.value,
      });
      success.value = "Регистрация успешна! Войдите.";
      isRegister.value = false;
      password.value = "";
      password2.value = "";
    } else {
      // ⭐ ИСПРАВЛЕНО: Используем authStore для логина
      await authStore.login(login.value, password.value);

      // Редирект на главную
      router.push("/");
    }
  } catch (e) {
    const data = e.response?.data;
    if (Array.isArray(data)) {
      data.forEach((err) => {
        if (err.loc?.includes("login")) errors.login = "Минимум 3 символа";
        if (err.loc?.includes("password"))
          errors.password = "Минимум 4 символа";
        if (err.loc?.includes("password_confirm"))
          errors.password2 = "Минимум 4 символа";
      });
    } else if (data?.detail) {
      if (data.detail.includes("already exists")) {
        errors.login = "Этот логин уже занят";
      } else if (data.detail.includes("Invalid")) {
        error.value = "Неверный логин или пароль";
      } else {
        error.value = data.detail;
      }
    } else {
      error.value = "Ошибка соединения с сервером";
    }
  } finally {
    loading.value = false;
  }
}
</script>

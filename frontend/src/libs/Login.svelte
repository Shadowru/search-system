<script>
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();

  let username = "";
  let password = "";
  let error = "";
  let isLoading = false;

  async function handleLogin() {
    isLoading = true;
    error = "";

    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    try {
      const res = await fetch('/api/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData
      });

      if (!res.ok) throw new Error('Неверный логин или пароль');

      const data = await res.json();
      // Сохраняем токен и сообщаем родителю
      localStorage.setItem('token', data.access_token);
      dispatch('loginSuccess');
      
    } catch (e) {
      error = e.message;
    } finally {
      isLoading = false;
    }
  }
</script>

<div class="login-container">
  <div class="card">
    <h2>🔐 Вход в систему</h2>
    <form on:submit|preventDefault={handleLogin}>
      <input type="text" bind:value={username} placeholder="Логин" required />
      <input type="password" bind:value={password} placeholder="Пароль" required />
      
      {#if error}
        <div class="error">{error}</div>
      {/if}

      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Вход...' : 'Войти'}
      </button>
    </form>
  </div>
</div>

<style>
  .login-container {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 80vh;
  }
  .card {
    background: white;
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    width: 100%;
    max-width: 350px;
    text-align: center;
  }
  input {
    width: 100%;
    padding: 10px;
    margin-bottom: 10px;
    border: 1px solid #ddd;
    border-radius: 6px;
    box-sizing: border-box;
  }
  button {
    width: 100%;
    padding: 10px;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: bold;
  }
  button:hover { background: #2563eb; }
  .error { color: red; margin-bottom: 10px; font-size: 0.9rem; }
</style>
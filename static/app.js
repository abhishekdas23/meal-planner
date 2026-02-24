document.addEventListener('alpine:init', () => {
  Alpine.data('app', () => ({
    // State
    view: 'login',
    token: null,
    userId: null,
    userName: '',
    pin: '',
    selectedUser: '',
    users: [],
    loginError: '',

    // Week view
    weekStart: null,  // Date object for Monday of current week
    meals: [],

    // Day view
    selectedDate: '',

    // Form
    showSheet: false,
    editingMeal: null,
    form: { name: '', portion: '', date: '', meal_time: 'breakfast' },

    mealTimes: [
      { key: 'breakfast', label: 'Breakfast' },
      { key: 'day_snack', label: 'Day Snack' },
      { key: 'lunch', label: 'Lunch' },
      { key: 'evening_snack', label: 'Evening Snack' },
      { key: 'dinner', label: 'Dinner' },
    ],

    async init() {
      // Check for saved session
      const saved = localStorage.getItem('meal_session');
      if (saved) {
        const s = JSON.parse(saved);
        this.token = s.token;
        this.userId = s.userId;
        this.userName = s.userName;
      }

      // Load users for login screen
      try {
        const res = await fetch('/api/auth/users');
        this.users = await res.json();
      } catch (e) { /* ignore */ }

      if (this.token) {
        this.view = 'week';
        this.initWeek();
        this.loadWeekMeals();
        this.connectSSE();
      }
    },

    // Auth
    async login() {
      this.loginError = '';
      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pin: this.pin, user_name: this.selectedUser }),
        });
        if (!res.ok) {
          const data = await res.json();
          this.loginError = data.detail || 'Login failed';
          return;
        }
        const data = await res.json();
        this.token = data.token;
        this.userId = data.user_id;
        this.userName = data.user_name;
        localStorage.setItem('meal_session', JSON.stringify({
          token: data.token, userId: data.user_id, userName: data.user_name,
        }));
        this.view = 'week';
        this.initWeek();
        this.loadWeekMeals();
        this.connectSSE();
      } catch (e) {
        this.loginError = 'Connection error';
      }
    },

    headers() {
      return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`,
      };
    },

    // Week helpers
    initWeek() {
      const today = new Date();
      const day = today.getDay();
      const diff = day === 0 ? -6 : 1 - day; // Monday
      this.weekStart = new Date(today);
      this.weekStart.setDate(today.getDate() + diff);
      this.weekStart.setHours(0, 0, 0, 0);
    },

    changeWeek(delta) {
      const d = new Date(this.weekStart);
      d.setDate(d.getDate() + delta * 7);
      this.weekStart = d;
      this.loadWeekMeals();
    },

    get weekLabel() {
      if (!this.weekStart) return '';
      const end = new Date(this.weekStart);
      end.setDate(end.getDate() + 6);
      const opts = { month: 'short', day: 'numeric' };
      return `${this.weekStart.toLocaleDateString('en-IN', opts)} – ${end.toLocaleDateString('en-IN', opts)}`;
    },

    get weekDays() {
      if (!this.weekStart) return [];
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const days = [];
      for (let i = 0; i < 7; i++) {
        const d = new Date(this.weekStart);
        d.setDate(d.getDate() + i);
        const iso = this.toISO(d);
        const dayMeals = this.meals.filter(m => m.date === iso);
        const filledSlots = new Set(dayMeals.map(m => m.meal_time)).size;
        days.push({
          date: iso,
          dayName: d.toLocaleDateString('en-IN', { weekday: 'short' }),
          dateLabel: d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }),
          isToday: d.getTime() === today.getTime(),
          mealSummary: dayMeals.length === 0 ? 'No meals' : `${filledSlots}/5 meal times`,
        });
      }
      return days;
    },

    get weekSummary() {
      if (!this.weekStart || this.meals.length === 0) return null;
      const totalMeals = this.meals.length;
      let fullDays = 0;
      for (let i = 0; i < 7; i++) {
        const d = new Date(this.weekStart);
        d.setDate(d.getDate() + i);
        const iso = this.toISO(d);
        const dayMeals = this.meals.filter(m => m.date === iso);
        const filledSlots = new Set(dayMeals.map(m => m.meal_time)).size;
        if (filledSlots === 5) fullDays++;
      }
      return { totalMeals, fullDays };
    },

    toISO(d) {
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${y}-${m}-${day}`;
    },

    // Data loading
    async loadWeekMeals() {
      if (!this.weekStart || !this.token) return;
      const weekStr = this.toISO(this.weekStart);
      try {
        const res = await fetch(`/api/meals?week=${weekStr}`, { headers: this.headers() });
        if (res.ok) {
          this.meals = await res.json();
        } else if (res.status === 401) {
          this.logout();
        }
      } catch (e) { /* ignore */ }
    },

    // Week summary detail
    get summaryDays() {
      if (!this.weekStart) return [];
      const days = [];
      for (let i = 0; i < 7; i++) {
        const d = new Date(this.weekStart);
        d.setDate(d.getDate() + i);
        const iso = this.toISO(d);
        const dayMeals = this.meals.filter(m => m.date === iso);
        if (dayMeals.length === 0) continue;
        const grouped = {};
        for (const mt of this.mealTimes) {
          const items = dayMeals.filter(m => m.meal_time === mt.key);
          if (items.length > 0) grouped[mt.label] = items;
        }
        days.push({
          label: d.toLocaleDateString('en-IN', { weekday: 'short', month: 'short', day: 'numeric' }),
          groups: grouped,
        });
      }
      return days;
    },

    // Navigation
    openDay(date) {
      this.selectedDate = date;
      this.view = 'day';
    },

    get selectedDayLabel() {
      if (!this.selectedDate) return '';
      const d = new Date(this.selectedDate + 'T00:00:00');
      return d.toLocaleDateString('en-IN', { weekday: 'long', month: 'long', day: 'numeric' });
    },

    getMealsFor(mealTime) {
      return this.meals.filter(m => m.date === this.selectedDate && m.meal_time === mealTime);
    },

    // CRUD
    openAddMeal() {
      this.editingMeal = null;
      this.form = {
        name: '',
        portion: '',
        date: this.selectedDate,
        meal_time: 'breakfast',
      };
      this.showSheet = true;
    },

    editMeal(meal) {
      this.editingMeal = meal;
      this.form = {
        name: meal.name,
        portion: meal.portion,
        date: meal.date,
        meal_time: meal.meal_time,
      };
      this.showSheet = true;
    },

    async saveMeal() {
      if (!this.form.name) return;
      try {
        let res;
        if (this.editingMeal) {
          res = await fetch(`/api/meals/${this.editingMeal.id}`, {
            method: 'PUT',
            headers: this.headers(),
            body: JSON.stringify(this.form),
          });
        } else {
          res = await fetch('/api/meals', {
            method: 'POST',
            headers: this.headers(),
            body: JSON.stringify(this.form),
          });
        }
        if (res.ok) {
          this.showSheet = false;
          this.loadWeekMeals();
        } else if (res.status === 401) {
          this.logout();
        }
      } catch (e) { /* ignore */ }
    },

    async deleteMeal(id) {
      if (!confirm('Delete this meal?')) return;
      try {
        const res = await fetch(`/api/meals/${id}`, {
          method: 'DELETE',
          headers: this.headers(),
        });
        if (res.ok) {
          this.loadWeekMeals();
        }
      } catch (e) { /* ignore */ }
    },

    // SSE
    connectSSE() {
      const es = new EventSource('/api/events');
      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          // Reload meals on any change
          this.loadWeekMeals();
        } catch (err) { /* ignore */ }
      };
      es.onerror = () => {
        // Reconnect after 5s
        es.close();
        setTimeout(() => this.connectSSE(), 5000);
      };
    },

    logout() {
      localStorage.removeItem('meal_session');
      this.token = null;
      this.view = 'login';
      this.pin = '';
      this.selectedUser = '';
    },
  }));
});

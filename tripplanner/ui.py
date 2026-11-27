from fastapi.responses import HTMLResponse


INDEX_HTML = """<!doctype html>
<html lang="uk">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>TripPlanner AI — планування подорожі</title>
    <style>
      :root {
        color-scheme: light;
        font-family: Inter, "Segoe UI", sans-serif;
        color: #17243b;
        background: #f3f6fb;
        font-synthesis: none;
      }
      * { box-sizing: border-box; }
      body { margin: 0; }
      main { width: min(900px, calc(100% - 32px)); margin: 36px auto 64px; }
      h1, h2, p { margin-top: 0; }
      h1 { margin-bottom: 8px; font-size: clamp(1.8rem, 5vw, 2.5rem); }
      .intro, .hint { color: #58677e; line-height: 1.55; }
      .service-state { margin: 20px 0; padding: 12px 16px; border-radius: 10px; background: #e8eef8; }
      .service-state[data-state="ok"] { background: #e7f6ec; color: #185b31; }
      .service-state[data-state="error"] { background: #fff0e8; color: #803b12; }
      .card { margin-top: 18px; padding: clamp(18px, 4vw, 30px); border: 1px solid #dfe6f0; border-radius: 16px; background: #fff; box-shadow: 0 8px 28px #17243b0b; }
      .steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 0 0 28px; padding: 0; list-style: none; }
      .steps li { padding: 11px 12px; border-bottom: 3px solid #dfe6f0; color: #68758a; font-size: .92rem; }
      .steps li[aria-current="step"] { border-color: #315fe8; color: #183da8; font-weight: 700; }
      .steps span { display: inline-grid; place-items: center; width: 25px; height: 25px; margin-right: 6px; border-radius: 50%; background: #eef1f6; }
      .steps li[aria-current="step"] span { background: #e8edff; }
      .field-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
      .field { display: grid; align-content: start; gap: 7px; }
      .field.full { grid-column: 1 / -1; }
      label, legend { font-weight: 650; }
      input, textarea { width: 100%; min-height: 44px; padding: 10px 12px; border: 1px solid #b9c5d6; border-radius: 8px; background: #fff; color: inherit; font: inherit; }
      textarea { min-height: 96px; resize: vertical; }
      input:focus, textarea:focus, button:focus-visible { outline: 3px solid #9db4ff; outline-offset: 2px; }
      [aria-invalid="true"] { border-color: #b42318; }
      .hint { margin: 0; font-size: .88rem; }
      .checkbox-row { display: flex; align-items: flex-start; gap: 10px; }
      .checkbox-row input { width: 18px; min-height: 18px; margin-top: 3px; }
      .actions { display: flex; flex-wrap: wrap; gap: 10px; justify-content: space-between; margin-top: 26px; }
      button { min-height: 44px; padding: 10px 18px; border: 0; border-radius: 8px; background: #315fe8; color: #fff; font: inherit; font-weight: 700; cursor: pointer; }
      button.secondary { border: 1px solid #b9c5d6; background: #fff; color: #263650; }
      button:disabled { cursor: wait; opacity: .65; }
      .notice { margin: 0; padding: 14px 16px; border-radius: 9px; background: #eef3ff; line-height: 1.5; }
      .notice.error { background: #fff0ee; color: #812018; }
      .review { display: grid; grid-template-columns: minmax(125px, .7fr) 1.3fr; gap: 10px 16px; margin: 18px 0 0; }
      .review dt { color: #58677e; }
      .review dd { margin: 0; font-weight: 600; overflow-wrap: anywhere; }
      .result-day { padding: 15px 0; border-top: 1px solid #e6ebf2; }
      .result-day h3 { margin: 0 0 8px; }
      .result-day ul { margin: 0; padding-left: 22px; line-height: 1.6; }
      .badges { display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0; }
      .badge { padding: 5px 10px; border-radius: 999px; background: #e9efff; color: #243f99; font-size: .85rem; font-weight: 650; }
      .warning { padding: 12px 14px; border-left: 4px solid #d68a1f; background: #fff7e8; line-height: 1.5; }
      [hidden] { display: none !important; }
      @media (max-width: 600px) {
        main { margin-top: 20px; }
        .steps li { padding: 8px 5px; font-size: .78rem; }
        .steps span { display: grid; margin: 0 auto 5px; }
        .field-grid { grid-template-columns: 1fr; }
        .field.full { grid-column: auto; }
        .review { grid-template-columns: 1fr; gap: 3px; }
        .review dd { margin-bottom: 9px; }
        .actions button { flex: 1 1 100%; }
      }
    </style>
  </head>
  <body>
    <main>
      <header>
        <h1>План подорожі — крок за кроком</h1>
        <p class="intro">Заповніть дані про подорож, перевірте побажання й натисніть «Створити план». Обов’язкові поля позначені браузером.</p>
        <p class="service-state" id="service-state" role="status" aria-live="polite">Перевіряємо доступність сервісу…</p>
      </header>

      <section class="card" aria-labelledby="form-title">
        <h2 id="form-title">Створення маршруту</h2>
        <ol class="steps" aria-label="Кроки створення плану">
          <li aria-current="step"><span>1</span>Подорож</li>
          <li><span>2</span>Побажання</li>
          <li><span>3</span>Перевірка</li>
        </ol>
        <form id="plan-form">
          <section class="step-panel" data-step="1" aria-labelledby="trip-title">
            <h3 id="trip-title">1. Куди й коли ви їдете?</h3>
            <p class="hint">Вкажіть напрямок, дати та загальний бюджет для всіх мандрівників.</p>
            <div class="field-grid">
              <div class="field full">
                <label for="destination">Місто або напрямок</label>
                <input id="destination" name="destination" required minlength="1" maxlength="100" autocomplete="off" aria-describedby="destination-help">
                <p class="hint" id="destination-help">Наприклад: Львів або Прага</p>
              </div>
              <div class="field">
                <label for="start-date">Дата початку</label>
                <input id="start-date" name="start_date" type="date" required>
              </div>
              <div class="field">
                <label for="end-date">Дата завершення</label>
                <input id="end-date" name="end_date" type="date" required aria-describedby="date-help">
                <p class="hint" id="date-help">Не більше ніж 31 календарний день.</p>
              </div>
              <div class="field">
                <label for="budget">Бюджет подорожі</label>
                <input id="budget" name="budget" type="number" min="0.01" max="9999999999.99" step="0.01" required>
              </div>
              <div class="field">
                <label for="currency">Валюта (код із 3 літер)</label>
                <input id="currency" name="currency" value="USD" pattern="[A-Za-z]{3}" maxlength="3" required aria-describedby="currency-help">
                <p class="hint" id="currency-help">Наприклад: UAH, EUR або USD</p>
              </div>
              <div class="field">
                <label for="travelers">Кількість мандрівників</label>
                <input id="travelers" name="traveler_count" type="number" min="1" max="20" value="1" step="1" required>
              </div>
            </div>
            <div class="actions">
              <span></span>
              <button type="button" data-next>Далі: побажання</button>
            </div>
          </section>

          <section class="step-panel" data-step="2" aria-labelledby="preferences-title" hidden>
            <h3 id="preferences-title">2. Що вас цікавить?</h3>
            <p class="hint">Побажання необов’язкові. Введіть до 10 пунктів — кожен з нового рядка або через кому.</p>
            <div class="field-grid">
              <div class="field full">
                <label for="interests">Інтереси</label>
                <textarea id="interests" name="interests" maxlength="900" aria-describedby="interests-help" placeholder="Наприклад: архітектура&#10;місцева кухня"></textarea>
                <p class="hint" id="interests-help">Кожен пункт — не довший за 80 символів.</p>
              </div>
              <div class="field full">
                <label for="constraints">Обмеження та важливі умови</label>
                <textarea id="constraints" name="constraints" maxlength="900" aria-describedby="constraints-help" placeholder="Наприклад: без тривалих піших маршрутів"></textarea>
                <p class="hint" id="constraints-help">Не додавайте секрети чи платіжні дані.</p>
              </div>
              <div class="field full">
                <label class="checkbox-row" for="weather-required">
                  <input id="weather-required" name="weather_required" type="checkbox">
                  <span>Для мене важлива інформація про погоду</span>
                </label>
                <p class="hint">Зараз сервіс не підключений до актуального джерела прогнозу погоди.</p>
              </div>
            </div>
            <div class="actions">
              <button type="button" class="secondary" data-back>Назад: подорож</button>
              <button type="button" data-next>Далі: перевірка</button>
            </div>
          </section>

          <section class="step-panel" data-step="3" aria-labelledby="review-title" hidden>
            <h3 id="review-title" tabindex="-1">3. Перевірте дані</h3>
            <p class="hint">Якщо все правильно, натисніть «Створити план». Не закривайте сторінку, поки обробляється запит.</p>
            <dl class="review" id="review"></dl>
            <div class="actions">
              <button type="button" class="secondary" data-back>Назад: побажання</button>
              <button type="submit" class="create-button">Створити план</button>
            </div>
          </section>
        </form>
        <p class="notice" id="status" role="status" aria-live="polite" hidden></p>
        <div id="result" aria-live="polite"></div>
      </section>

      <section class="card" id="last-plan" aria-labelledby="last-plan-title" hidden>
        <h2 id="last-plan-title">Останній створений план</h2>
        <p class="hint">Пробуємо відновити план за його ID. Це спрацює, поки серверне сховище не буде очищено.</p>
        <div id="restored-result"></div>
      </section>
    </main>
    <script>
      const ownerId = "demo-user";
      const form = document.querySelector("#plan-form");
      const status = document.querySelector("#status");
      const result = document.querySelector("#result");
      const serviceState = document.querySelector("#service-state");
      const panels = [...document.querySelectorAll(".step-panel")];
      const stepMarkers = [...document.querySelectorAll(".steps li")];
      const fields = {
        destination: document.querySelector("#destination"),
        start_date: document.querySelector("#start-date"),
        end_date: document.querySelector("#end-date"),
        budget: document.querySelector("#budget"),
        currency: document.querySelector("#currency"),
        traveler_count: document.querySelector("#travelers"),
        interests: document.querySelector("#interests"),
        constraints: document.querySelector("#constraints")
      };
      let currentStep = 1;
      let retryTimer;

      function showStep(step) {
        currentStep = step;
        panels.forEach((panel) => { panel.hidden = Number(panel.dataset.step) !== step; });
        stepMarkers.forEach((marker, index) => {
          if (index + 1 === step) marker.setAttribute("aria-current", "step");
          else marker.removeAttribute("aria-current");
        });
        document.querySelector(`#${step === 1 ? "destination" : step === 2 ? "interests" : "review-title"}`).focus();
        if (step === 3) renderReview();
      }

      function parseList(value) {
        return value.split(/[\\n,]/).map((item) => item.trim()).filter(Boolean);
      }

      function validateStepOne() {
        const destination = fields.destination;
        destination.setCustomValidity(destination.value.trim() ? "" : "Введіть напрямок подорожі.");
        const start = fields.start_date.value;
        const end = fields.end_date.value;
        fields.end_date.setCustomValidity("");
        if (start && end && end < start) {
          fields.end_date.setCustomValidity("Дата завершення має бути не раніше дати початку.");
        } else if (start && end && (Date.parse(end) - Date.parse(start)) / 86400000 > 30) {
          fields.end_date.setCustomValidity("Подорож не може тривати довше ніж 31 календарний день.");
        }
        return !panels[0].querySelector(":invalid");
      }

      function validateStepTwo() {
        for (const [name, field] of [["interests", fields.interests], ["constraints", fields.constraints]]) {
          const values = parseList(field.value);
          if (values.length > 10 || values.some((value) => value.length > 80)) {
            field.setCustomValidity(name === "interests"
              ? "Вкажіть не більше ніж 10 інтересів, кожен до 80 символів."
              : "Вкажіть не більше ніж 10 обмежень, кожне до 80 символів.");
          } else {
            field.setCustomValidity("");
          }
        }
        return !panels[1].querySelector(":invalid");
      }

      function showInvalidField(panel) {
        const invalid = panel.querySelector(":invalid");
        if (invalid) {
          invalid.focus();
          invalid.reportValidity();
        }
      }

      function requestPayload() {
        return {
          destination: fields.destination.value.trim(),
          start_date: fields.start_date.value,
          end_date: fields.end_date.value,
          budget: Number(fields.budget.value),
          currency: fields.currency.value.trim().toUpperCase(),
          traveler_count: Number(fields.traveler_count.value),
          interests: parseList(fields.interests.value),
          constraints: parseList(fields.constraints.value),
          weather_required: document.querySelector("#weather-required").checked
        };
      }

      function renderReview() {
        const payload = requestPayload();
        const entries = [
          ["Напрямок", payload.destination],
          ["Дати", `${payload.start_date} — ${payload.end_date}`],
          ["Бюджет", `${payload.budget} ${payload.currency}`],
          ["Мандрівники", String(payload.traveler_count)],
          ["Інтереси", payload.interests.join(", ") || "Не вказані"],
          ["Обмеження", payload.constraints.join(", ") || "Не вказані"],
          ["Погода", payload.weather_required ? "Важлива (актуальний прогноз не підключено)" : "Не обов’язково"]
        ];
        const review = document.querySelector("#review");
        review.replaceChildren();
        for (const [label, value] of entries) {
          const term = document.createElement("dt");
          const description = document.createElement("dd");
          term.textContent = label;
          description.textContent = value;
          review.append(term, description);
        }
      }

      function clearFieldErrors() {
        Object.values(fields).forEach((field) => {
          field.removeAttribute("aria-invalid");
          const errorId = `server-error-${field.name}`;
          const descriptions = (field.getAttribute("aria-describedby") || "")
            .split(/\\s+/)
            .filter((id) => id && id !== errorId);
          if (descriptions.length) field.setAttribute("aria-describedby", descriptions.join(" "));
          else field.removeAttribute("aria-describedby");
        });
        document.querySelectorAll("[data-server-error]").forEach((node) => node.remove());
      }

      function showServerFieldErrors(names) {
        clearFieldErrors();
        let targetStep = 1;
        for (const name of names) {
          const field = fields[name];
          if (!field) continue;
          field.setAttribute("aria-invalid", "true");
          const message = document.createElement("span");
          message.dataset.serverError = "true";
          message.id = `server-error-${name}`;
          message.className = "hint";
          message.textContent = "Перевірте це поле.";
          const descriptions = field.getAttribute("aria-describedby");
          field.setAttribute("aria-describedby", [descriptions, message.id].filter(Boolean).join(" "));
          field.insertAdjacentElement("afterend", message);
          if (name === "interests" || name === "constraints") targetStep = 2;
        }
        showStep(targetStep);
        const firstInvalid = panels[targetStep - 1].querySelector('[aria-invalid="true"]');
        if (firstInvalid) firstInvalid.focus();
      }

      function displayPlan(plan, target) {
        const title = document.createElement("h2");
        title.textContent = `Ваш план подорожі: ${plan.destination}`;
        target.replaceChildren(title);

        const badges = document.createElement("div");
        badges.className = "badges";
        const sourceNames = {
          main: "Основний результат",
          fallback: "Резервний результат",
          cache: "Із кешу",
          mock: "Демонстраційний режим (mock)",
          recorded: "Збережений приклад (recorded)"
        };
        const source = document.createElement("span");
        source.className = "badge";
        source.textContent = sourceNames[plan.source] || "Джерело не вказане";
        badges.append(source);
        const budget = document.createElement("span");
        budget.className = "badge";
        budget.textContent = `Бюджет: ${plan.budget} ${plan.currency}`;
        badges.append(budget);
        target.append(badges);

        if (plan.missing_data && plan.missing_data.length) {
          const warning = document.createElement("p");
          warning.className = "warning";
          warning.textContent = "Увага: для цього плану не підтверджено актуальність таких даних: "
            + plan.missing_data.map((item) => ({
              live_weather: "погода",
              current_prices: "поточні ціни",
              opening_hours: "години роботи",
              budget_estimates: "оцінки витрат"
            }[item] || item)).join(", ")
            + ". Перевірте їх перед подорожжю.";
          target.append(warning);
        }

        for (const day of plan.days) {
          const article = document.createElement("article");
          article.className = "result-day";
          const heading = document.createElement("h3");
          heading.textContent = day.date;
          const list = document.createElement("ul");
          for (const activity of day.activities) {
            const item = document.createElement("li");
            item.textContent = activity;
            list.append(item);
          }
          article.append(heading, list);
          if (day.estimated_cost !== null && day.estimated_cost !== undefined) {
            const cost = document.createElement("p");
            cost.className = "hint";
            cost.textContent = `Орієнтовні витрати за день: ${day.estimated_cost} ${plan.currency}`;
            article.append(cost);
          }
          target.append(article);
        }
        if (target === result) {
          const newPlan = document.createElement("button");
          newPlan.type = "button";
          newPlan.className = "secondary";
          newPlan.textContent = "Створити інший план";
          newPlan.addEventListener("click", () => {
            result.replaceChildren();
            status.hidden = true;
            showStep(1);
            fields.destination.focus();
          });
          target.append(newPlan);
        }
      }

      function setStatus(message, isError = false) {
        status.hidden = false;
        status.classList.toggle("error", isError);
        status.textContent = message;
      }

      document.querySelectorAll("[data-next]").forEach((button) => {
        button.addEventListener("click", () => {
          if (currentStep === 1) {
            if (validateStepOne()) showStep(2);
            else showInvalidField(panels[0]);
          } else if (currentStep === 2) {
            if (validateStepTwo()) showStep(3);
            else showInvalidField(panels[1]);
          }
        });
      });
      document.querySelectorAll("[data-back]").forEach((button) => {
        button.addEventListener("click", () => showStep(currentStep - 1));
      });

      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!validateStepOne()) {
          showStep(1);
          showInvalidField(panels[0]);
          return;
        }
        if (!validateStepTwo()) {
          showStep(2);
          showInvalidField(panels[1]);
          return;
        }
        clearFieldErrors();
        const createButton = document.querySelector(".create-button");
        createButton.disabled = true;
        let waitingForRetry = false;
        result.replaceChildren();
        setStatus("Запит надіслано. Сервер формує план — зачекайте на відповідь…");
        try {
          const response = await fetch("/api/v1/plans", {
            method: "POST",
            headers: {"Content-Type": "application/json", "X-Owner-ID": ownerId},
            body: JSON.stringify(requestPayload())
          });
          const body = await response.json();
          if (!response.ok) {
            const error = body.error || {};
            const requestInfo = error.request_id ? ` Номер запиту: ${error.request_id}.` : "";
            if (response.status === 422 && Array.isArray(error.fields)) {
              showServerFieldErrors(error.fields);
              setStatus(`Сервер відхилив введені дані. Перевірте позначені поля.${requestInfo}`, true);
            } else if (error.retryable) {
              const retryAfter = Number(response.headers.get("Retry-After") || error.retry_after || 0);
              setStatus(
                `Тимчасово не вдалося створити план. ${retryAfter > 0 ? `Зачекайте ${retryAfter} с і повторіть спробу.` : "Спробуйте ще раз."}${requestInfo}`,
                true
              );
              if (retryAfter > 0) {
                waitingForRetry = true;
                const retryAt = Date.now() + retryAfter * 1000;
                createButton.disabled = true;
                clearInterval(retryTimer);
                retryTimer = setInterval(() => {
                  const seconds = Math.ceil((retryAt - Date.now()) / 1000);
                  if (seconds <= 0) {
                    clearInterval(retryTimer);
                    createButton.disabled = false;
                    setStatus("Тепер можна повторити спробу.");
                  } else {
                    setStatus(`Тимчасово не вдалося створити план. Повторіть спробу через ${seconds} с.${requestInfo}`, true);
                  }
                }, 250);
              }
            } else {
              const errorMessages = {
                rate_limited: "Забагато запитів. Спробуйте пізніше.",
                daily_budget_exceeded: "Денний ліміт витрат на AI вичерпано.",
                provider_unavailable: "Сервіс планування тимчасово недоступний.",
                provider_timeout: "Час очікування відповіді сервісу вичерпано.",
                invalid_output: "Сервіс планування повернув некоректний результат.",
                not_found: "План не знайдено.",
                internal: "Сталася неочікувана помилка."
              };
              setStatus(`${errorMessages[error.code] || "Не вдалося створити план."}${requestInfo}`, true);
            }
            return;
          }
          sessionStorage.setItem("tripplanner:lastPlanId", body.id);
          setStatus("План створено. Перед подорожжю перевірте актуальні ціни та іншу інформацію.");
          displayPlan(body, result);
          result.scrollIntoView({behavior: "smooth", block: "start"});
        } catch {
          setStatus("Не вдалося зв’язатися із сервером. Перевірте підключення й повторіть спробу.", true);
        } finally {
          if (!waitingForRetry) createButton.disabled = false;
        }
      });

      async function checkService() {
        try {
          const response = await fetch("/health");
          if (!response.ok) throw new Error("Не вдалося перевірити доступність сервісу.");
          const health = await response.json();
          serviceState.dataset.state = "ok";
          const providerNames = {mock: "демонстраційний", openai_compat: "OpenAI-сумісний"};
          serviceState.textContent = `Сервіс доступний. Режим: ${providerNames[health.checks.provider] || "невідомий"}.`;
        } catch {
          serviceState.dataset.state = "error";
          serviceState.textContent = "Не вдалося перевірити сервіс. Перевірте з’єднання; форму можна заповнити й спробувати пізніше.";
        }
      }

      async function restoreLastPlan() {
        const planId = sessionStorage.getItem("tripplanner:lastPlanId");
        if (!planId) return;
        const section = document.querySelector("#last-plan");
        const target = document.querySelector("#restored-result");
        section.hidden = false;
        try {
          const response = await fetch(`/api/v1/plans/${encodeURIComponent(planId)}`, {
            headers: {"X-Owner-ID": ownerId}
          });
          if (!response.ok) throw new Error("План більше недоступний.");
          displayPlan(await response.json(), target);
        } catch {
          sessionStorage.removeItem("tripplanner:lastPlanId");
          target.textContent = "План більше недоступний (наприклад, сервер перезапустився й очистив пам’ять). Створіть новий план у формі вище.";
        }
      }

      checkService();
      restoreLastPlan();
    </script>
  </body>
</html>
"""


def index_page() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)

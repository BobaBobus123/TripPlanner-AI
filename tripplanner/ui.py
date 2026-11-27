from fastapi.responses import HTMLResponse


INDEX_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>TripPlanner AI</title>
  </head>
  <body>
    <main>
      <h1>TripPlanner AI</h1>
      <p>Generate a deterministic demo itinerary. Live prices and weather are not included.</p>
      <form id="plan-form">
        <label for="destination">Destination</label>
        <input id="destination" name="destination" required maxlength="100">
        <label for="start-date">Start date</label>
        <input id="start-date" name="start_date" type="date" required>
        <label for="end-date">End date</label>
        <input id="end-date" name="end_date" type="date" required>
        <label for="budget">Budget</label>
        <input id="budget" name="budget" type="number" min="0.01" step="0.01" required>
        <label for="currency">Currency (3 letters)</label>
        <input id="currency" name="currency" value="USD" pattern="[A-Za-z]{3}" required>
        <label for="travelers">Travelers</label>
        <input id="travelers" name="traveler_count" type="number" min="1" max="20" value="1" required>
        <button type="submit">Create itinerary</button>
      </form>
      <p id="status" role="status" aria-live="polite"></p>
      <pre id="result"></pre>
    </main>
    <script>
      const form = document.querySelector("#plan-form");
      const status = document.querySelector("#status");
      const result = document.querySelector("#result");
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        const values = new FormData(form);
        const payload = Object.fromEntries(values.entries());
        payload.budget = Number(payload.budget);
        payload.traveler_count = Number(payload.traveler_count);
        status.textContent = "Creating plan...";
        result.textContent = "";
        try {
          const response = await fetch("/api/v1/plans", {
            method: "POST",
            headers: {"Content-Type": "application/json", "X-Owner-ID": "demo-user"},
            body: JSON.stringify(payload)
          });
          const body = await response.json();
          status.textContent = response.ok ? "Plan created." : body.error.message;
          result.textContent = JSON.stringify(body, null, 2);
        } catch {
          status.textContent = "The server could not be reached.";
        }
      });
    </script>
  </body>
</html>
"""


def index_page() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)

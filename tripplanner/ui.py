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
        color: #172a28;
        background: #f5f7f4;
        font-synthesis: none;
        --ink: #172a28;
        --muted: #64736e;
        --line: #e1e8e2;
        --surface: #fff;
        --canvas: #f5f7f4;
        --green: #176b53;
        --green-dark: #10513f;
        --green-soft: #e8f4ee;
        --amber: #92610f;
        --red: #a63d32;
      }
      * { box-sizing: border-box; }
      body { margin: 0; }
      button, input, textarea, select { font: inherit; }
      a { color: inherit; }
      .site-shell { min-height: 100vh; }
      .sidebar {
        position: fixed; inset: 0 auto 0 0; z-index: 5; display: flex; flex-direction: column;
        width: 248px; padding: 28px 18px 20px; border-right: 1px solid var(--line);
        background: var(--surface);
      }
      .brand { display: flex; align-items: center; gap: 11px; margin: 0 8px 36px; text-decoration: none; }
      .brand-mark {
        display: grid; width: 40px; height: 40px; place-items: center; border-radius: 14px;
        background: var(--green); color: #fff; font-size: 1.15rem; font-weight: 800;
      }
      .brand-copy { display: grid; gap: 2px; }
      .brand-copy strong { font-size: 1rem; letter-spacing: -.02em; }
      .brand-copy small { color: var(--muted); font-size: .72rem; }
      .nav-label { margin: 0 10px 10px; color: #8a9690; font-size: .68rem; font-weight: 750; letter-spacing: .12em; }
      .primary-nav { display: grid; gap: 6px; }
      .nav-link {
        display: flex; min-height: 46px; align-items: center; gap: 12px; padding: 0 12px;
        border-radius: 12px; color: #52615b; font-size: .92rem; font-weight: 620; text-decoration: none;
        transition: background .16s ease, color .16s ease;
      }
      .nav-link:hover { background: #f3f7f4; color: var(--ink); }
      .nav-link[aria-current="page"] { background: var(--green-soft); color: var(--green-dark); }
      .nav-icon { display: grid; width: 25px; place-items: center; font-size: 1.05rem; }
      .sidebar-create { display: flex; min-height: 48px; align-items: center; justify-content: center; gap: 8px; margin: 22px 4px; }
      .sidebar-note { margin-top: auto; padding: 16px 14px; border: 1px solid var(--line); border-radius: 14px; background: #f8faf8; }
      .sidebar-note strong { display: block; margin-bottom: 5px; font-size: .84rem; }
      .sidebar-note p { margin: 0; color: var(--muted); font-size: .78rem; line-height: 1.5; }
      .main-panel { min-height: 100vh; margin-left: 248px; }
      .topbar {
        position: sticky; top: 0; z-index: 4; display: flex; min-height: 92px; align-items: center;
        justify-content: space-between; gap: 20px; padding: 15px clamp(22px, 4vw, 54px);
        border-bottom: 1px solid #e8ede8; background: rgb(255 255 255 / 92%); backdrop-filter: blur(14px);
      }
      .topbar-title { display: grid; gap: 4px; }
      .eyebrow { margin: 0; color: var(--green); font-size: .69rem; font-weight: 800; letter-spacing: .13em; text-transform: uppercase; }
      .topbar h1 { margin: 0; font-size: clamp(1.1rem, 2vw, 1.38rem); letter-spacing: -.035em; }
      .account-actions { display: flex; align-items: center; gap: 12px; }
      .account-email { max-width: 220px; overflow: hidden; color: var(--muted); font-size: .85rem; text-overflow: ellipsis; white-space: nowrap; }
      .avatar { display: grid; width: 36px; height: 36px; place-items: center; border-radius: 50%; background: #e8f4ee; color: var(--green-dark); font-size: .85rem; font-weight: 750; }
      .content { width: min(1160px, 100%); margin: 0 auto; padding: 32px clamp(18px, 4vw, 54px) 72px; }
      h1, h2, h3, p { margin-top: 0; }
      h2 { letter-spacing: -.025em; }
      .intro, .hint { color: var(--muted); line-height: 1.6; }
      .page-view { animation: page-in .22s ease-out; }
      @keyframes page-in { from { opacity: .5; transform: translateY(5px); } to { opacity: 1; transform: none; } }
      .welcome-panel {
        position: relative; display: flex; min-height: 250px; align-items: center; justify-content: space-between;
        gap: 30px; overflow: hidden; padding: clamp(28px, 5vw, 52px); border-radius: 24px;
        background: linear-gradient(112deg, #123f35 0%, #176b53 62%, #258466 100%); color: #fff;
      }
      .welcome-copy { position: relative; z-index: 1; max-width: 550px; }
      .welcome-copy .eyebrow { margin-bottom: 13px; color: #bce7d4; }
      .welcome-copy h2 { max-width: 520px; margin-bottom: 13px; font-size: clamp(1.8rem, 3.3vw, 2.7rem); line-height: 1.08; letter-spacing: -.045em; }
      .welcome-copy p:not(.eyebrow) { max-width: 480px; margin-bottom: 22px; color: #d7eee4; line-height: 1.6; }
      .welcome-art { position: absolute; right: 4%; bottom: -44%; width: min(340px, 38%); aspect-ratio: 1; border: 1px solid #ffffff27; border-radius: 50%; background: #ffffff0b; }
      .welcome-art::before, .welcome-art::after { position: absolute; content: ""; border: 1px solid #ffffff34; border-radius: 50%; }
      .welcome-art::before { inset: 13%; }
      .welcome-art::after { inset: 27%; background: #ffffff12; }
      .welcome-pin { position: absolute; top: 12%; left: 45%; z-index: 1; display: grid; width: 48px; height: 48px; place-items: center; border: 6px solid #ffffff2a; border-radius: 50%; background: #d9f3e5; color: var(--green-dark); font-size: 1rem; font-weight: 800; }
      .button {
        display: inline-flex; min-height: 46px; align-items: center; justify-content: center; gap: 9px;
        padding: 0 18px; border: 1px solid transparent; border-radius: 11px; background: var(--green);
        color: #fff; font-weight: 720; text-decoration: none; cursor: pointer;
        transition: transform .16s ease, background .16s ease, box-shadow .16s ease;
      }
      .button:hover { transform: translateY(-1px); background: var(--green-dark); box-shadow: 0 6px 16px #104b3921; }
      .button.light { background: #fff; color: var(--green-dark); }
      .button.light:hover { background: #eff8f2; }
      .button.secondary { border-color: #d8e2da; background: #fff; color: #344840; }
      .button.secondary:hover { background: #f6f9f6; }
      .button.small { min-height: 38px; padding: 0 13px; font-size: .83rem; }
      .button:disabled { transform: none; cursor: wait; opacity: .6; }
      .stats-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin: 20px 0 34px; }
      .stat-card { display: flex; min-height: 112px; align-items: center; gap: 15px; padding: 18px; border: 1px solid var(--line); border-radius: 17px; background: var(--surface); }
      .stat-icon { display: grid; width: 43px; height: 43px; flex: 0 0 auto; place-items: center; border-radius: 14px; background: var(--green-soft); color: var(--green-dark); font-size: 1.1rem; font-weight: 800; }
      .stat-card p { margin: 0 0 4px; color: var(--muted); font-size: .78rem; }
      .stat-card strong { display: block; font-size: 1.15rem; letter-spacing: -.02em; }
      .section-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 0 0 15px; }
      .section-heading h2 { margin: 0; font-size: 1.15rem; }
      .text-link { color: var(--green); font-size: .88rem; font-weight: 720; text-decoration: none; }
      .text-link:hover { text-decoration: underline; }
      .trip-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
      .trip-card { display: flex; min-height: 190px; flex-direction: column; padding: 19px; border: 1px solid var(--line); border-radius: 17px; background: var(--surface); transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease; }
      .trip-card:hover { transform: translateY(-2px); border-color: #c9ded0; box-shadow: 0 10px 28px #17372b0d; }
      .trip-card-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 17px; }
      .trip-card h3 { margin: 0 0 6px; font-size: 1.06rem; overflow-wrap: anywhere; }
      .trip-card-date { margin-bottom: 16px; color: var(--muted); font-size: .82rem; }
      .trip-card .button { width: fit-content; margin-top: auto; }
      .status-pill { display: inline-flex; align-items: center; gap: 6px; padding: 5px 9px; border-radius: 999px; background: #f0f3f1; color: #596760; font-size: .71rem; font-weight: 750; white-space: nowrap; }
      .status-pill::before { width: 6px; height: 6px; border-radius: 50%; background: currentColor; content: ""; }
      .status-pill[data-status="completed"] { background: var(--green-soft); color: var(--green-dark); }
      .status-pill[data-status="failed"], .status-pill[data-status="cancelled"], .status-pill[data-status="interrupted"] { background: #fff0ed; color: var(--red); }
      .status-pill[data-status="generating"], .status-pill[data-status="validating"], .status-pill[data-status="preparing"], .status-pill[data-status="queued"] { background: #fff5df; color: var(--amber); }
      .empty-state { padding: 34px 20px; border: 1px dashed #cbd8ce; border-radius: 17px; background: #fbfcfb; text-align: center; }
      .empty-icon { display: grid; width: 48px; height: 48px; margin: 0 auto 12px; place-items: center; border-radius: 16px; background: var(--green-soft); color: var(--green); font-size: 1.25rem; }
      .empty-state h3 { margin-bottom: 6px; font-size: 1rem; }
      .empty-state p { margin: 0 auto 17px; color: var(--muted); font-size: .87rem; line-height: 1.5; }
      .list-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 18px; }
      .list-toolbar p { margin: 0; color: var(--muted); font-size: .87rem; }
      .trip-list { display: grid; gap: 11px; }
      .trip-row { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; align-items: center; gap: 18px; padding: 17px 19px; border: 1px solid var(--line); border-radius: 15px; background: #fff; }
      .trip-row h3 { margin: 0 0 5px; font-size: .98rem; }
      .trip-row p { margin: 0; color: var(--muted); font-size: .8rem; }
      .card { padding: clamp(20px, 3vw, 30px); border: 1px solid var(--line); border-radius: 20px; background: var(--surface); box-shadow: 0 6px 24px #172a2806; }
      .new-page-heading { margin-bottom: 19px; }
      .new-page-heading h2 { margin: 6px 0; font-size: clamp(1.45rem, 2.6vw, 1.9rem); }
      .new-page-heading p { max-width: 680px; margin: 0; color: var(--muted); line-height: 1.55; }
      .steps { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 9px; margin: 0 0 28px; padding: 0; list-style: none; }
      .steps li { display: flex; min-height: 49px; align-items: center; gap: 9px; padding: 8px 11px; border: 1px solid #e4e9e5; border-radius: 12px; color: #758078; font-size: .82rem; font-weight: 620; }
      .steps li[aria-current="step"] { border-color: #bedac9; background: #f1f8f3; color: var(--green-dark); font-weight: 750; }
      .steps span { display: grid; width: 27px; height: 27px; flex: 0 0 auto; place-items: center; border-radius: 50%; background: #edf1ed; font-size: .78rem; }
      .steps li[aria-current="step"] span { background: var(--green); color: #fff; }
      .field-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 17px; }
      .field { display: grid; align-content: start; gap: 7px; }
      .field.full { grid-column: 1 / -1; }
      label, legend { color: #34443d; font-size: .88rem; font-weight: 700; }
      input, textarea, select { width: 100%; min-height: 47px; padding: 11px 13px; border: 1px solid #d6dfd8; border-radius: 11px; background: #fff; color: inherit; font-size: .94rem; transition: border-color .15s ease, box-shadow .15s ease; }
      textarea { min-height: 100px; resize: vertical; }
      input:focus, textarea:focus, select:focus, button:focus-visible, a:focus-visible { outline: 3px solid #a9d8bd; outline-offset: 2px; }
      input:focus, textarea:focus, select:focus { border-color: #64a983; box-shadow: 0 0 0 3px #dcefe3; }
      [aria-invalid="true"] { border-color: #b42318; }
      .hint { margin: 0; font-size: .82rem; }
      .checkbox-row { display: flex; align-items: flex-start; gap: 10px; }
      .checkbox-row input { width: 18px; min-height: 18px; margin-top: 3px; accent-color: var(--green); }
      .actions { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; justify-content: space-between; margin-top: 27px; }
      .notice { margin: 16px 0 0; padding: 13px 15px; border: 1px solid #dbe8df; border-radius: 12px; background: #f2f8f4; color: #365044; line-height: 1.5; }
      .notice.error { border-color: #f2d2ce; background: #fff3f1; color: #812018; }
      .review { display: grid; grid-template-columns: minmax(125px, .7fr) 1.3fr; gap: 10px 16px; margin: 18px 0 0; }
      .review dt { color: var(--muted); }
      .review dd { margin: 0; font-weight: 600; overflow-wrap: anywhere; }
      .result-day { display: grid; grid-template-columns: 140px minmax(0, 1fr); gap: 12px; padding: 20px 0; border-top: 1px solid var(--line); }
      .result-day h3 { margin: 2px 0 0; font-size: .95rem; }
      .result-day ul { margin: 0; padding-left: 19px; color: #3a4b43; line-height: 1.65; }
      .badges { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 20px; }
      .badge { padding: 6px 10px; border: 1px solid #dce9df; border-radius: 999px; background: #f2f8f3; color: #345b44; font-size: .78rem; font-weight: 680; }
      .warning { margin: 0 0 17px; padding: 13px 15px; border: 1px solid #f1e2bd; border-radius: 12px; background: #fff9eb; color: #70531b; line-height: 1.5; }
      .live-info { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 18px 0 24px; }
      .live-card { min-height: 150px; padding: 16px; border: 1px solid var(--line); border-radius: 16px; background: linear-gradient(145deg, #ffffff, #f7faf8); }
      .live-card h3 { display: flex; align-items: center; gap: 8px; margin: 0 0 10px; font-size: .92rem; }
      .live-card ul { margin: 0; padding: 0; list-style: none; }
      .live-card li { padding: 7px 0; border-top: 1px solid #edf1ee; color: #405148; font-size: .78rem; line-height: 1.45; }
      .live-card li:first-child { border-top: 0; }
      .live-card strong { display: block; color: var(--ink); }
      .live-card .source { display: block; margin-top: 10px; color: var(--muted); font-size: .68rem; }
      .live-source { grid-column: 1 / -1; margin: 0; color: var(--muted); font-size: .72rem; line-height: 1.5; }
      .guide-strip { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 14px 0 22px; }
      .guide-step { padding: 12px 13px; border: 1px solid #dce8df; border-radius: 13px; background: #fbfdfb; color: #526158; font-size: .78rem; line-height: 1.45; }
      .guide-step strong { display: block; margin-bottom: 3px; color: var(--ink); }
      .auth-page { width: min(480px, 100%); margin: 5vh auto 0; padding: clamp(23px, 5vw, 42px); }
      .auth-brand { display: flex; align-items: center; gap: 10px; margin-bottom: 26px; }
      .auth-page h2 { margin-bottom: 7px; font-size: 1.6rem; }
      .auth-page .button { width: 100%; min-height: 52px; }
      .auth-page .field-grid { gap: 16px; }
      .auth-page .actions { margin-top: 20px; }
      .auth-page .text-link { display: inline-flex; min-height: 44px; align-items: center; }
      .auth-form-actions { display: grid; gap: 10px; margin-top: 18px; }
      .verify-actions { display: grid; gap: 12px; margin-top: 20px; }
      .verify-resend-field { margin-top: 22px; }
      .verify-resend-button { margin-top: 12px; }
      .verify-link { overflow-wrap: anywhere; }
      .service-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 0 0 22px; }
      .service-state { display: inline-flex; align-items: center; gap: 8px; margin: 0; padding: 10px 12px; border-radius: 10px; background: #edf2ee; color: #53635a; font-size: .79rem; }
      .service-state::before { width: 7px; height: 7px; border-radius: 50%; background: #a5b1a8; content: ""; }
      .service-state[data-state="ok"]::before { background: #3c9b68; }
      .service-state[data-state="error"] { background: #fff0e8; color: #803b12; }
      .service-state[data-state="error"]::before { background: #b84d39; }
      .service-check { min-height: 36px; padding: 0 12px; font-size: .78rem; }
      .ai-mode-note { width: 100%; margin: 0; color: var(--muted); font-size: .8rem; line-height: 1.5; }
      .detail-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; margin-bottom: 18px; }
      .detail-heading h2 { margin: 4px 0 6px; font-size: clamp(1.45rem, 3vw, 2rem); overflow-wrap: anywhere; }
      .detail-heading p { margin: 0; color: var(--muted); font-size: .88rem; }
      .progress-card { margin-bottom: 18px; }
      .job-summary { display: flex; align-items: center; gap: 12px; margin: 14px 0 18px; }
      .job-message { margin: 0; color: #354a40; font-weight: 650; line-height: 1.5; }
      .indeterminate { width: 30px; height: 30px; flex: 0 0 auto; accent-color: var(--green); }
      .progress-steps { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; margin: 18px 0 0; padding: 0; list-style: none; }
      .progress-steps li { display: grid; gap: 8px; color: #849088; font-size: .72rem; line-height: 1.3; }
      .progress-steps li::before { width: 100%; height: 4px; border-radius: 99px; background: #e7ece8; content: ""; }
      .progress-steps li[data-step-state="done"]::before { background: #64a983; }
      .progress-steps li[data-step-state="current"]::before { background: var(--green); }
      .progress-steps li[data-step-state="current"] { color: var(--green-dark); font-weight: 760; }
      .job-result { margin-top: 22px; }
      .job-result > h2 { margin-bottom: 6px; font-size: 1.25rem; }
      .workflow-card { margin: 0 0 18px; padding: 20px 22px; border: 1px solid #dce8df; border-radius: 17px; background: #f9fbf9; }
      .workflow-card h3 { margin: 0 0 12px; font-size: 1rem; }
      .workflow-steps { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 0; padding: 0; list-style: none; }
      .workflow-steps li { color: var(--muted); font-size: .78rem; line-height: 1.5; }
      .workflow-steps strong { display: block; margin-bottom: 4px; color: var(--ink); font-size: .82rem; }
      .workflow-disclosure { margin: 14px 0 0; color: var(--muted); font-size: .78rem; line-height: 1.5; }
      .provider-settings { margin: 0 0 28px; }
      .provider-settings h2 { margin: 0; font-size: 1.1rem; }
      .provider-settings-copy { margin: 0 0 14px; color: var(--muted); font-size: .84rem; line-height: 1.5; }
      .provider-controls { display: grid; grid-template-columns: minmax(200px, 1fr) auto; align-items: end; gap: 12px; }
      .provider-control { display: grid; gap: 7px; }
      .provider-settings-status { margin: 12px 0 0; color: var(--muted); font-size: .82rem; line-height: 1.5; }
      .service-state[data-state="ok"] { background: #edf2ee; }
      .account-actions button { min-height: 38px; padding: 0 12px; }
      [hidden] { display: none !important; }
      .site-shell:not(.is-authenticated) .sidebar, .site-shell:not(.is-authenticated) .topbar { display: none; }
      .site-shell:not(.is-authenticated) .main-panel { margin-left: 0; }
      @media (max-width: 980px) {
        .sidebar { width: 220px; }
        .main-panel { margin-left: 220px; }
        .trip-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .welcome-art { right: -2%; }
      }
      @media (max-width: 720px) {
        .sidebar { inset: auto 0 0; width: auto; height: 68px; flex-direction: row; align-items: center; padding: 6px 10px calc(6px + env(safe-area-inset-bottom)); border: 0; border-top: 1px solid var(--line); }
        .brand, .nav-label, .sidebar-create, .sidebar-note { display: none; }
        .primary-nav { display: grid; width: 100%; grid-template-columns: repeat(3, 1fr); gap: 4px; }
        .nav-link { min-height: 52px; flex-direction: column; justify-content: center; gap: 1px; padding: 3px; font-size: .68rem; }
        .nav-icon { width: auto; font-size: 1rem; }
        .main-panel { margin-left: 0; padding-bottom: 70px; }
        .topbar { position: static; min-height: 76px; padding: 12px 18px; }
        .content { padding: 20px 16px 38px; }
        .welcome-panel { min-height: 255px; padding: 26px 23px; }
        .welcome-art { right: -26%; bottom: -36%; width: 70%; opacity: .75; }
        .stats-grid { grid-template-columns: 1fr; gap: 9px; margin: 14px 0 28px; }
        .stat-card { min-height: 82px; padding: 13px 15px; }
        .trip-grid { grid-template-columns: 1fr; }
        .trip-card { min-height: 165px; }
        .trip-row { grid-template-columns: minmax(0, 1fr) auto; gap: 10px; }
        .trip-row .status-pill { grid-column: 1; grid-row: 2; justify-self: start; }
        .trip-row .button { grid-column: 2; grid-row: 1 / span 2; }
        .steps { gap: 5px; }
        .steps li { min-height: 66px; flex-direction: column; justify-content: center; gap: 4px; padding: 6px 3px; text-align: center; font-size: .68rem; }
        .field-grid { grid-template-columns: 1fr; }
        .field.full { grid-column: auto; }
        .review { grid-template-columns: 1fr; gap: 3px; }
        .review dd { margin-bottom: 9px; }
        .actions { align-items: stretch; }
        .live-info { grid-template-columns: 1fr; }
        .guide-strip { grid-template-columns: 1fr; }
        .actions .button, .actions button { flex: 1 1 100%; }
        .detail-heading { flex-direction: column; }
        .result-day { grid-template-columns: 1fr; gap: 8px; }
        .progress-steps { gap: 4px; }
        .progress-steps li { font-size: .6rem; }
        .account-email { max-width: 145px; }
        .workflow-steps { grid-template-columns: 1fr 1fr; }
        .provider-controls { grid-template-columns: 1fr; }
      }
      @media (max-width: 390px) {
        .topbar { align-items: flex-start; }
        .account-actions { gap: 6px; }
        .account-email { max-width: 105px; font-size: .74rem; }
      }
    </style>
  </head>
  <body>
    <div class="site-shell" id="site-shell">
      <aside class="sidebar" aria-label="Головна навігація">
        <a class="brand" href="/dashboard" data-nav>
          <span class="brand-mark" aria-hidden="true">Т</span>
          <span class="brand-copy"><strong>TripPlanner AI</strong><small>Подорожі без метушні</small></span>
        </a>
        <p class="nav-label">МЕНЮ</p>
        <nav class="primary-nav">
          <a class="nav-link" href="/dashboard" data-nav data-page-link="dashboard"><span class="nav-icon" aria-hidden="true">⌂</span>Огляд</a>
          <a class="nav-link" href="/trips" data-nav data-page-link="trips"><span class="nav-icon" aria-hidden="true">▤</span>Мої подорожі</a>
          <a class="nav-link" href="/new" data-nav data-page-link="new"><span class="nav-icon" aria-hidden="true">＋</span>Створити план</a>
        </nav>
        <a class="button sidebar-create" href="/new" data-nav>＋ Нова подорож</a>
        <div class="sidebar-note">
          <strong>Сплануйте у своєму темпі</strong>
          <p>Ваші маршрути зберігаються в обліковому записі, щоб ви могли повернутися до них пізніше.</p>
        </div>
      </aside>

      <div class="main-panel">
        <header class="topbar">
          <div class="topbar-title">
            <p class="eyebrow" id="page-eyebrow">Ваш простір</p>
            <h1 id="page-title">Огляд подорожей</h1>
          </div>
          <div class="account-actions" id="account-actions" hidden>
            <span class="avatar" id="avatar-initial" aria-hidden="true"></span>
            <span class="account-email" id="account-email"></span>
            <button type="button" class="button secondary small" id="logout-button">Вийти</button>
          </div>
        </header>

        <main class="content">
          <div class="service-bar">
            <p class="service-state" id="service-state" role="status" aria-live="polite">Перевіряємо доступність сервісу…</p>
            <button type="button" class="button secondary service-check" id="check-service">Перевірити з’єднання</button>
            <p class="ai-mode-note" id="ai-mode-note"></p>
          </div>

          <section class="card auth-page" id="auth-card" aria-labelledby="auth-title">
            <div class="auth-brand">
              <span class="brand-mark" aria-hidden="true">Т</span>
              <span class="brand-copy"><strong>TripPlanner AI</strong><small>Ваш помічник у подорожах</small></span>
            </div>
            <p class="eyebrow">Ласкаво просимо</p>
            <section id="login-panel" data-auth-view="login" aria-labelledby="auth-title">
              <h2 id="auth-title">Увійдіть до свого простору</h2>
              <p class="hint">Після входу ваші плани й збережені подорожі будуть під рукою.</p>
              <form id="login-form">
                <div class="field-grid">
                  <div class="field full">
                    <label for="login-email">Електронна пошта</label>
                    <input id="login-email" name="email" type="email" autocomplete="email" required maxlength="254">
                  </div>
                  <div class="field full">
                    <label for="login-password">Пароль</label>
                    <input id="login-password" name="password" type="password" autocomplete="current-password" required minlength="1" maxlength="128">
                  </div>
                </div>
                <div class="auth-form-actions">
                  <button type="submit" class="button">Увійти</button>
                  <a class="button secondary" href="/register" data-nav>Створити обліковий запис</a>
                </div>
              </form>
            </section>
            <section id="register-panel" data-auth-view="register" aria-labelledby="register-title" hidden>
              <h2 id="register-title">Створіть обліковий запис</h2>
              <p class="hint">Вкажіть електронну пошту та створіть пароль. Після реєстрації можна одразу увійти.</p>
              <form id="register-form">
                <div class="field-grid">
                  <div class="field full">
                    <label for="register-email">Електронна пошта</label>
                    <input id="register-email" name="email" type="email" autocomplete="email" required maxlength="254">
                  </div>
                  <div class="field full">
                    <label for="register-password">Пароль</label>
                    <input id="register-password" name="password" type="password" autocomplete="new-password" required minlength="12" maxlength="128" aria-describedby="register-password-help">
                    <p class="hint" id="register-password-help">Щонайменше 12 символів.</p>
                  </div>
                  <div class="field full">
                    <label for="register-password-confirm">Повторіть пароль</label>
                    <input id="register-password-confirm" name="password_confirm" type="password" autocomplete="new-password" required minlength="12" maxlength="128" aria-describedby="password-confirm-help">
                    <p class="hint" id="password-confirm-help">Переконайтеся, що обидва паролі збігаються.</p>
                  </div>
                </div>
                <div class="auth-form-actions">
                  <button type="submit" class="button">Зареєструватися</button>
                  <a class="button secondary" href="/login" data-nav>Уже маєте обліковий запис? Увійти</a>
                </div>
              </form>
            </section>
            <section id="verify-panel" data-auth-view="verify" aria-labelledby="verify-title" hidden>
              <h2 id="verify-title">Підтвердьте електронну пошту</h2>
              <p class="hint" id="verify-description">Відкрийте посилання з листа, а потім підтвердьте адресу кнопкою нижче.</p>
              <div class="verify-actions">
                <button type="button" class="button" id="verify-button">Підтвердити пошту</button>
                <a class="button secondary" href="/login" data-nav>Перейти до входу</a>
              </div>
              <form id="resend-form">
                <div class="field full verify-resend-field">
                  <label for="resend-email">Не отримали лист?</label>
                  <input id="resend-email" name="email" type="email" autocomplete="email" required maxlength="254" aria-describedby="resend-help">
                  <p class="hint" id="resend-help">Вкажіть пошту — надішлемо нове посилання, якщо обліковий запис очікує підтвердження.</p>
                </div>
                <button type="submit" class="button secondary verify-resend-button">Надіслати лист повторно</button>
              </form>
              <div id="development-verification" class="notice" hidden></div>
            </section>
            <p class="notice" id="auth-status" role="status" aria-live="polite" hidden></p>
          </section>

          <div id="workspace" hidden>
            <section class="page-view" id="dashboard-page" data-view="dashboard">
              <div class="welcome-panel">
                <div class="welcome-copy">
                  <p class="eyebrow">ДОРОГА ПОЧИНАЄТЬСЯ ТУТ</p>
                  <h2 id="dashboard-welcome">Куди вирушимо цього разу?</h2>
                  <p>Задайте напрямок і дати — ми допоможемо скласти зрозумілий план, до якого зручно повертатися.</p>
                  <a class="button light" href="/new" data-nav>＋ Спланувати подорож</a>
                </div>
                <div class="welcome-art" aria-hidden="true"><span class="welcome-pin">Т</span></div>
              </div>

              <div class="stats-grid" aria-label="Підсумок подорожей">
                <article class="stat-card">
                  <span class="stat-icon" aria-hidden="true">▤</span>
                  <div><p>Усього подорожей</p><strong id="trip-count">0</strong></div>
                </article>
                <article class="stat-card">
                  <span class="stat-icon" aria-hidden="true">◷</span>
                  <div><p>Зараз у роботі</p><strong id="active-count">0</strong></div>
                </article>
                <article class="stat-card">
                  <span class="stat-icon" aria-hidden="true">↗</span>
                  <div><p>Останній напрямок</p><strong id="last-trip-destination">Ще не обрано</strong></div>
                </article>
              </div>

              <section class="card provider-settings" id="provider-settings" aria-labelledby="provider-settings-title" hidden>
                <div class="section-heading">
                  <h2 id="provider-settings-title">Глобальний режим AI</h2>
                  <span class="status-pill" id="provider-mode-pill"></span>
                </div>
                <p class="provider-settings-copy">Режим застосовується до нових подорожей для всього застосунку. OpenAI API може тарифікувати запити; уже створені завдання завершуються в початковому режимі.</p>
                <div class="provider-controls" id="provider-controls" hidden>
                  <div class="provider-control">
                    <label for="provider-mode">Генератор плану</label>
                    <select id="provider-mode">
                      <option value="mock">Демонстраційний mock — без виклику AI API</option>
                      <option value="openai_compat">OpenAI API — використовується ключ із сервера</option>
                    </select>
                  </div>
                  <button type="button" class="button" id="save-provider-mode">Зберегти режим</button>
                </div>
                <p class="provider-settings-status" id="provider-settings-status" role="status" aria-live="polite"></p>
              </section>

              <div class="section-heading">
                <h2>Останні подорожі</h2>
                <a class="text-link" href="/trips" data-nav>Усі подорожі →</a>
              </div>
              <div class="trip-grid" id="dashboard-trip-list"></div>
              <div class="empty-state" id="dashboard-empty" hidden>
                <span class="empty-icon" aria-hidden="true">＋</span>
                <h3>Тут з’явиться ваша перша подорож</h3>
                <p>Додайте напрямок, дати й побажання — решту можна спокійно перевірити перед створенням плану.</p>
                <a class="button" href="/new" data-nav>Створити першу подорож</a>
              </div>
            </section>

            <section class="page-view" id="trips-page" data-view="trips" hidden>
              <div class="section-heading">
                <div><p class="eyebrow">ВАША ІСТОРІЯ</p><h2>Мої подорожі</h2></div>
                <a class="button small" href="/new" data-nav>＋ Нова подорож</a>
              </div>
              <div class="list-toolbar"><p id="trips-summary">Завантажуємо список…</p></div>
              <div class="trip-list" id="history-list"></div>
            </section>

            <section class="page-view" id="new-trip-page" data-view="new" hidden>
              <div class="new-page-heading">
                <p class="eyebrow">НОВА ПОДОРОЖ</p>
                <h2>Створімо план, який підійде саме вам</h2>
                <p>Рухайтеся крок за кроком. Ваші дані можна перевірити перед надсиланням.</p>
              </div>
              <aside class="workflow-card" aria-labelledby="workflow-title">
                <h3 id="workflow-title">Як створюється план</h3>
                <ol class="workflow-steps">
                  <li><strong>1. Ваші побажання</strong>Напрямок, дати, бюджет та інтереси з цієї форми.</li>
                  <li><strong>2. Запит до сервера</strong>Сервер формує структурований запит і передає його вибраному провайдеру.</li>
                  <li><strong>3. Перевірка</strong>Сервер перевіряє формат, дати та відповідність результату вашому запиту.</li>
                  <li><strong>4. Збережений план</strong>Етапи надходять у реальному часі; готовий результат можна відкрити пізніше.</li>
                </ol>
                <p class="workflow-disclosure">Цей сайт не підключений до чату Copilot. У режимі реального провайдера дані подорожі надсилаються налаштованому AI-сервісу. Актуальна погода, ціни та години роботи не перевіряються.</p>
              </aside>
              <section class="card" aria-labelledby="form-title">
                <h2 id="form-title">Деталі подорожі</h2>
                <ol class="steps" aria-label="Кроки створення плану">
                  <li aria-current="step"><span>1</span>Подорож</li>
                  <li><span>2</span>Побажання</li>
                  <li><span>3</span>Перевірка</li>
                </ol>
                <div class="guide-strip" aria-label="Підказка: як заповнювати план">
                  <div class="guide-step"><strong>1. Напрямок</strong>Вкажіть місто або конкретну область.</div>
                  <div class="guide-step"><strong>2. Побажання</strong>Додайте інтереси й обмеження у вільному вигляді.</div>
                  <div class="guide-step"><strong>3. Перевірка</strong>Перед створенням перегляньте всі дані й змініть їх за потреби.</div>
                </div>
                <form id="plan-form">
                  <section class="step-panel" data-step="1" aria-labelledby="trip-title">
                    <h3 id="trip-title">1. Куди й коли ви їдете?</h3>
                    <p class="hint">Вкажіть напрямок, дати та спільний бюджет для всіх мандрівників.</p>
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
                      <button type="button" class="button" data-next>Далі: побажання</button>
                    </div>
                  </section>

                  <section class="step-panel" data-step="2" aria-labelledby="preferences-title" hidden>
                    <h3 id="preferences-title">2. Що вам подобається?</h3>
                    <p class="hint">Цей крок необов’язковий. Додайте до 10 побажань — кожне з нового рядка або через кому.</p>
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
                        <p class="hint">Актуальний прогноз погоди поки не підключений.</p>
                      </div>
                    </div>
                    <div class="actions">
                      <button type="button" class="button secondary" data-back>Назад: подорож</button>
                      <button type="button" class="button" data-next>Далі: перевірка</button>
                    </div>
                  </section>

                  <section class="step-panel" data-step="3" aria-labelledby="review-title" hidden>
                    <h3 id="review-title" tabindex="-1">3. Перевірте дані</h3>
                    <p class="hint">Переконайтеся, що все правильно. Після створення план буде збережено в «Моїх подорожах».</p>
                    <dl class="review" id="review"></dl>
                    <div class="actions">
                      <button type="button" class="button secondary" data-back>Назад: побажання</button>
                      <button type="submit" class="button create-button">Створити план</button>
                    </div>
                  </section>
                </form>
                <p class="notice" id="status" role="status" aria-live="polite" hidden></p>
              </section>
            </section>

            <section class="page-view" id="trip-detail-page" data-view="detail" hidden>
              <div class="detail-heading">
                <div>
                  <p class="eyebrow">ПОДОРОЖ</p>
                  <h2 id="detail-title">Завантажуємо подорож…</h2>
                  <p id="detail-dates"></p>
                  <span class="status-pill" id="detail-provider-mode"></span>
                </div>
                <a class="button secondary small" href="/trips" data-nav>← До подорожей</a>
              </div>
              <section class="card progress-card" id="job-progress" aria-labelledby="progress-title" data-state="queued">
                <div class="section-heading">
                  <h2 id="progress-title">Стан плану</h2>
                  <span class="status-pill" id="detail-status"></span>
                </div>
                <div class="job-summary">
                  <progress class="indeterminate" id="job-progress-bar" aria-label="План створюється"></progress>
                  <p class="job-message" id="job-message" role="status" aria-live="polite"></p>
                </div>
                <ol class="progress-steps" id="progress-steps" aria-label="Етапи створення плану">
                  <li data-stage="queued">У черзі</li>
                  <li data-stage="preparing">Підготовка</li>
                  <li data-stage="generating">Створення маршруту</li>
                  <li data-stage="validating">Перевірка плану</li>
                  <li data-stage="completed">Готовий</li>
                </ol>
                <div class="actions">
                  <span class="hint">Можна залишити цю сторінку — стан збережеться.</span>
                  <button type="button" class="button secondary" id="cancel-job">Скасувати створення</button>
                </div>
                <div class="job-result" id="job-result" aria-live="polite"></div>
              </section>
            </section>
          </div>
        </main>
      </div>
    </div>
    <script>
      const form = document.querySelector("#plan-form");
      const status = document.querySelector("#status");
      const serviceState = document.querySelector("#service-state");
      const shell = document.querySelector("#site-shell");
      const panels = [...document.querySelectorAll(".step-panel")];
      const stepMarkers = [...document.querySelectorAll(".steps li")];
      const pageTitles = {
        login: ["ОБЛІКОВИЙ ЗАПИС", "Вхід"],
        register: ["ОБЛІКОВИЙ ЗАПИС", "Реєстрація"],
        verify: ["ПІДТВЕРДЖЕННЯ", "Перевірка пошти"],
        dashboard: ["Ваш простір", "Огляд подорожей"],
        trips: ["ВАША ІСТОРІЯ", "Мої подорожі"],
        new: ["НОВА ПОДОРОЖ", "Створення плану"],
        detail: ["ПОДОРОЖ", "Деталі подорожі"]
      };
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
      let pendingSubmission = null;
      let currentUser = null;
      let currentProviderMode = "mock";
      let csrfToken = "";
      let verificationToken = "";
      let authNotice = "";
      let activeJobId = null;
      let activeEventSource = null;
      let statusPollTimer = null;

      function getIdempotencyKey(payload) {
        const fingerprint = JSON.stringify({
          payload,
          provider_mode: currentProviderMode
        });
        if (pendingSubmission && pendingSubmission.fingerprint === fingerprint) {
          return pendingSubmission.key;
        }
        try {
          const saved = JSON.parse(sessionStorage.getItem("tripplanner:pendingSubmission") || "null");
          if (saved && saved.fingerprint === fingerprint && saved.key) {
            pendingSubmission = saved;
            return saved.key;
          }
        } catch {
          sessionStorage.removeItem("tripplanner:pendingSubmission");
        }
        pendingSubmission = {
          fingerprint,
          key: crypto.randomUUID()
        };
        sessionStorage.setItem("tripplanner:pendingSubmission", JSON.stringify(pendingSubmission));
        return pendingSubmission.key;
      }

      async function apiFetch(url, options = {}) {
        const headers = new Headers(options.headers || {});
        if (options.method && !["GET", "HEAD", "OPTIONS"].includes(options.method.toUpperCase())) {
          headers.set("X-CSRF-Token", csrfToken);
        }
        return fetch(url, {...options, headers, credentials: "same-origin"});
      }

      function showWorkspace(user) {
        currentUser = user;
        document.querySelector("#auth-card").hidden = true;
        document.querySelector("#workspace").hidden = false;
        shell.classList.add("is-authenticated");
        document.querySelector("#account-actions").hidden = false;
        document.querySelector("#account-email").textContent = user.email;
        document.querySelector("#avatar-initial").textContent = user.email.slice(0, 1).toUpperCase();
        document.querySelector("#login-password").value = "";
        document.querySelector("#register-password").value = "";
        document.querySelector("#register-password-confirm").value = "";
        renderRoute();
      }

      function requireLogin(message) {
        stopJobUpdates();
        currentUser = null;
        csrfToken = "";
        shell.classList.remove("is-authenticated");
        document.querySelector("#account-actions").hidden = true;
        document.querySelector("#workspace").hidden = true;
        document.querySelector("#auth-card").hidden = false;
        window.history.replaceState(null, "", "/login");
        renderRoute();
        showAuthMessage(message);
      }

      function showAuthMessage(message, isError = false) {
        const authStatus = document.querySelector("#auth-status");
        authStatus.hidden = false;
        authStatus.classList.toggle("error", isError);
        authStatus.textContent = message;
      }

      async function authenticate() {
        const authForm = document.querySelector("#login-form");
        if (!authForm.reportValidity()) return;
        const email = document.querySelector("#login-email").value.trim();
        const password = document.querySelector("#login-password").value;
        const buttons = authForm.querySelectorAll("button");
        buttons.forEach((button) => { button.disabled = true; });
        showAuthMessage("Входимо…");
        try {
          const response = await fetch("/api/v1/auth/login", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            credentials: "same-origin",
            body: JSON.stringify({email, password})
          });
          const body = await response.json();
          if (!response.ok) {
            const messages = {
              unauthorized: "Не вдалося увійти. Перевірте пошту й пароль.",
              email_not_verified: "Підтвердьте пошту за посиланням із листа. Якщо листа немає, перейдіть до перевірки пошти.",
              rate_limited: "Забагато спроб входу. Спробуйте пізніше."
            };
            const retryAfter = response.headers.get("Retry-After");
            const message = messages[body.error?.code] || body.error?.message || "Не вдалося виконати запит.";
            showAuthMessage(message + (retryAfter ? ` Спробуйте через ${retryAfter} с.` : ""), true);
            if (body.error?.code === "email_not_verified") {
              document.querySelector("#resend-email").value = email;
              navigateTo("/verify-email");
              showAuthMessage(message, true);
            }
            return;
          }
          csrfToken = body.csrf_token;
          showWorkspace(body.user);
          document.querySelector("#auth-status").hidden = true;
          await loadTrips();
          await loadProviderSettings();
          await restoreLastJob();
        } catch {
          await checkService();
          showAuthMessage(`Не вдалося виконати запит до ${window.location.origin}. Перевірте стан сервера вище.`, true);
        } finally {
          buttons.forEach((button) => { button.disabled = false; });
        }
      }

      async function registerAccount() {
        const registerForm = document.querySelector("#register-form");
        const password = document.querySelector("#register-password");
        const passwordConfirm = document.querySelector("#register-password-confirm");
        passwordConfirm.setCustomValidity(
          password.value === passwordConfirm.value ? "" : "Паролі не збігаються."
        );
        if (!registerForm.reportValidity()) return;
        const buttons = registerForm.querySelectorAll("button");
        buttons.forEach((button) => { button.disabled = true; });
        showAuthMessage("Створюємо обліковий запис…");
        try {
          const response = await fetch("/api/v1/auth/register", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            credentials: "same-origin",
            body: JSON.stringify({
              email: document.querySelector("#register-email").value.trim(),
              password: password.value
            })
          });
          const body = await response.json();
          if (!response.ok) {
            const retryAfter = response.headers.get("Retry-After");
            const message = body.error?.message || "Не вдалося створити обліковий запис.";
            showAuthMessage(message + (retryAfter ? ` Спробуйте через ${retryAfter} с.` : ""), true);
            return;
          }
          const email = document.querySelector("#register-email").value.trim();
          authNotice = body.message;
          await navigateTo("/login");
          document.querySelector("#login-email").value = email;
          showAuthMessage(body.message);
        } catch {
          showAuthMessage("Не вдалося надіслати запит. Перевірте з’єднання та спробуйте ще раз.", true);
        } finally {
          buttons.forEach((button) => { button.disabled = false; });
        }
      }

      async function verifyEmail() {
        if (!verificationToken) {
          showAuthMessage("У посиланні немає токена. Надішліть лист повторно.", true);
          return;
        }
        const button = document.querySelector("#verify-button");
        button.disabled = true;
        showAuthMessage("Перевіряємо посилання…");
        try {
          const response = await fetch("/api/v1/auth/verify-email", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            credentials: "same-origin",
            body: JSON.stringify({token: verificationToken})
          });
          const body = await response.json();
          if (!response.ok) {
            showAuthMessage(body.error?.message || "Не вдалося підтвердити пошту.", true);
            return;
          }
          authNotice = body.message;
          verificationToken = "";
          await navigateTo("/login");
          showAuthMessage(authNotice);
        } catch {
          showAuthMessage("Не вдалося перевірити посилання. Спробуйте ще раз.", true);
        } finally {
          button.disabled = false;
        }
      }

      async function resendVerification(event) {
        event.preventDefault();
        const resendForm = document.querySelector("#resend-form");
        if (!resendForm.reportValidity()) return;
        const button = resendForm.querySelector("button");
        button.disabled = true;
        showAuthMessage("Надсилаємо лист, якщо обліковий запис очікує підтвердження…");
        try {
          const response = await fetch("/api/v1/auth/resend-verification", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            credentials: "same-origin",
            body: JSON.stringify({email: document.querySelector("#resend-email").value.trim()})
          });
          const body = await response.json();
          if (!response.ok) {
            const retryAfter = response.headers.get("Retry-After");
            showAuthMessage(
              body.error?.message || "Не вдалося надіслати лист.",
              true
            );
            if (retryAfter) showAuthMessage(`Спробуйте через ${retryAfter} с.`, true);
            return;
          }
          showAuthMessage(body.message);
          if (body.verification_url) {
            const verificationUrl = new URL(body.verification_url, window.location.origin);
            if (verificationUrl.origin === window.location.origin) {
              const note = document.querySelector("#development-verification");
              note.replaceChildren();
              const link = document.createElement("a");
              link.className = "text-link verify-link";
              link.href = `${verificationUrl.pathname}${verificationUrl.search}${verificationUrl.hash}`;
              link.textContent = "Відкрити нове посилання для підтвердження";
              link.dataset.nav = "";
              note.append(link);
              note.hidden = false;
            }
          }
        } catch {
          showAuthMessage("Не вдалося надіслати запит. Перевірте з’єднання.", true);
        } finally {
          button.disabled = false;
        }
      }

      async function restoreSession() {
        try {
          const response = await fetch("/api/v1/auth/me", {credentials: "same-origin"});
          if (!response.ok) {
            renderRoute();
            return;
          }
          const body = await response.json();
          csrfToken = body.csrf_token;
          showWorkspace(body.user);
          await loadTrips();
          await loadProviderSettings();
          await restoreLastJob();
        } catch {
          showAuthMessage("Не вдалося перевірити обліковий запис. Оновіть сторінку.", true);
        }
      }

      function statusLabel(status) {
        return ({
          queued: "У черзі",
          preparing: "Підготовка",
          generating: "Створюємо маршрут",
          validating: "Перевіряємо план",
          cancel_requested: "Скасовуємо",
          completed: "Готово",
          failed: "Помилка",
          cancelled: "Скасовано",
          interrupted: "Перервано"
        })[status] || status;
      }

      async function loadProviderSettings() {
        const panel = document.querySelector("#provider-settings");
        const controls = document.querySelector("#provider-controls");
        const message = document.querySelector("#provider-settings-status");
        try {
          const response = await apiFetch("/api/v1/settings/provider");
          if (response.status === 401) {
            requireLogin("Сеанс завершився. Увійдіть знову.");
            return null;
          }
          if (!response.ok) throw new Error("Не вдалося завантажити налаштування AI.");
          const settings = await response.json();
          currentProviderMode = settings.mode;
          const modeSelect = document.querySelector("#provider-mode");
          const saveButton = document.querySelector("#save-provider-mode");
          const openAiOption = modeSelect.querySelector('option[value="openai_compat"]');
          openAiOption.disabled = !settings.available_modes.includes("openai_compat");
          modeSelect.value = settings.mode;
          saveButton.disabled = modeSelect.value === settings.mode;
          controls.hidden = !settings.is_admin;
          panel.hidden = !settings.is_admin && settings.admin_configured;

          const modeName = settings.mode === "mock" ? "Демонстраційний mock" : "OpenAI API";
          const modePill = document.querySelector("#provider-mode-pill");
          modePill.textContent = modeName;
          modePill.dataset.status = settings.mode === "mock" ? "queued" : "completed";

          if (!settings.admin_configured) {
            message.textContent = "Панель власника не активована. Додайте APP_ADMIN_EMAIL зі своєю адресою облікового запису до локального .env і перезапустіть сервер.";
          } else if (settings.is_admin && !settings.available_modes.includes("openai_compat")) {
            message.textContent = "OpenAI API поки недоступний: додайте OPENAI_COMPAT_API_KEY та актуальні INPUT_COST_PER_MILLION_TOKENS і OUTPUT_COST_PER_MILLION_TOKENS у .env. Не вставляйте ключ у браузер.";
          } else if (settings.is_admin) {
            const model = settings.model ? ` Модель: ${settings.model}.` : "";
            message.textContent = `${modeName} діє для нових завдань у всьому застосунку.${model}`;
          }
          return settings;
        } catch {
          panel.hidden = false;
          message.textContent = "Не вдалося завантажити режим AI. Перевірте з’єднання та повторіть спробу.";
          return null;
        }
      }

      function routeForPath(pathname) {
        if (pathname === "/login") return {page: "login"};
        if (pathname === "/register") return {page: "register"};
        if (pathname === "/verify-email") {
          return {
            page: "verify",
            token: new URLSearchParams(window.location.hash.slice(1)).get("token") || ""
          };
        }
        if (pathname === "/" || pathname === "/dashboard") return {page: "dashboard"};
        if (pathname === "/trips") return {page: "trips"};
        if (pathname === "/new") return {page: "new"};
        const detail = pathname.match(/^\\/trips\\/([0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$/i);
        return detail ? {page: "detail", jobId: detail[1]} : null;
      }

      function renderRoute() {
        let route = routeForPath(window.location.pathname);
        if (!route) {
          const path = currentUser ? "/dashboard" : "/login";
          window.history.replaceState(null, "", path);
          route = {page: currentUser ? "dashboard" : "login"};
        }
        const authPages = ["login", "register", "verify"];
        if (!currentUser && !authPages.includes(route.page)) {
          window.history.replaceState(null, "", "/login");
          route = {page: "login"};
        } else if (currentUser && authPages.includes(route.page)) {
          window.history.replaceState(null, "", "/dashboard");
          route = {page: "dashboard"};
        }
        verificationToken = route.page === "verify" ? route.token : "";
        document.querySelector("#auth-card").hidden = Boolean(currentUser);
        document.querySelector("#workspace").hidden = !currentUser;
        document.querySelectorAll("[data-auth-view]").forEach((view) => {
          view.hidden = view.dataset.authView !== route.page;
        });
        const verificationLink = document.querySelector("#development-verification");
        if (route.page !== "verify") verificationLink.hidden = true;
        if (route.page === "verify" && !verificationToken) {
          document.querySelector("#verify-description").textContent =
            "Відкрийте посилання з листа або надішліть його повторно за формою нижче.";
          document.querySelector("#verify-button").hidden = true;
        } else if (route.page === "verify") {
          document.querySelector("#verify-description").textContent =
            "Посилання знайдено. Натисніть кнопку, щоб підтвердити адресу.";
          document.querySelector("#verify-button").hidden = false;
        }
        document.querySelectorAll("[data-view]").forEach((view) => {
          view.hidden = view.dataset.view !== route.page;
        });
        const [eyebrow, title] = pageTitles[route.page];
        document.querySelector("#page-eyebrow").textContent = eyebrow;
        document.querySelector("#page-title").textContent = title;
        document.title = `${title} — TripPlanner AI`;
        if (route.page === "new") {
          status.hidden = true;
          status.classList.remove("error");
          clearFieldErrors();
          showStep(1);
        }
        document.querySelectorAll("[data-page-link]").forEach((link) => {
          const current = link.dataset.pageLink === route.page
            || (route.page === "detail" && link.dataset.pageLink === "trips");
          if (current) link.setAttribute("aria-current", "page");
          else link.removeAttribute("aria-current");
        });
        return route;
      }

      async function navigateTo(path, replace = false) {
        if (replace) window.history.replaceState(null, "", path);
        else window.history.pushState(null, "", path);
        const route = renderRoute();
        if (route.page === "detail") {
          await openJob(route.jobId);
        } else {
          stopJobUpdates();
        }
      }

      document.addEventListener("click", (event) => {
        const link = event.target.closest("a[data-nav]");
        if (!link || event.defaultPrevented || event.button !== 0
          || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        const target = new URL(link.href, window.location.href);
        if (target.origin !== window.location.origin) return;
        const route = routeForPath(target.pathname);
        if (!route) return;
        event.preventDefault();
        navigateTo(`${target.pathname}${target.search}${target.hash}`);
      });

      window.addEventListener("popstate", async () => {
        const route = renderRoute();
        if (route.page === "detail") await openJob(route.jobId);
        else stopJobUpdates();
      });

      function formattedTripDates(job) {
        if (job.start_date && job.end_date) {
          const start = new Date(`${job.start_date}T00:00:00`);
          const end = new Date(`${job.end_date}T00:00:00`);
          return `${start.toLocaleDateString("uk-UA")} — ${end.toLocaleDateString("uk-UA")}`;
        }
        return `Створено ${new Date(job.created_at).toLocaleDateString("uk-UA")}`;
      }

      function createTripCard(job) {
        const card = document.createElement("article");
        card.className = "trip-card";
        const top = document.createElement("div");
        top.className = "trip-card-top";
        const icon = document.createElement("span");
        icon.className = "stat-icon";
        icon.setAttribute("aria-hidden", "true");
        icon.textContent = "↗";
        const badge = document.createElement("span");
        badge.className = "status-pill";
        badge.dataset.status = job.status;
        badge.textContent = statusLabel(job.status);
        top.append(icon, badge);
        const heading = document.createElement("h3");
        heading.textContent = job.destination || "Подорож";
        const dates = document.createElement("p");
        dates.className = "trip-card-date";
        dates.textContent = formattedTripDates(job);
        const link = document.createElement("a");
        link.className = "button secondary small";
        link.href = `/trips/${encodeURIComponent(job.id)}`;
        link.dataset.nav = "";
        link.textContent = "Відкрити план →";
        card.append(top, heading, dates, link);
        return card;
      }

      function createTripRow(job) {
        const row = document.createElement("article");
        row.className = "trip-row";
        const info = document.createElement("div");
        const heading = document.createElement("h3");
        heading.textContent = job.destination || "Подорож";
        const dates = document.createElement("p");
        dates.textContent = formattedTripDates(job);
        info.append(heading, dates);
        const badge = document.createElement("span");
        badge.className = "status-pill";
        badge.dataset.status = job.status;
        badge.textContent = statusLabel(job.status);
        const link = document.createElement("a");
        link.className = "button secondary small";
        link.href = `/trips/${encodeURIComponent(job.id)}`;
        link.dataset.nav = "";
        link.textContent = "Відкрити";
        row.append(info, badge, link);
        return row;
      }

      async function loadTrips() {
        const list = document.querySelector("#history-list");
        const dashboardList = document.querySelector("#dashboard-trip-list");
        const dashboardEmpty = document.querySelector("#dashboard-empty");
        try {
          const response = await apiFetch("/api/v1/jobs");
          if (response.status === 401) {
            requireLogin("Сеанс завершився. Увійдіть знову.");
            return;
          }
          if (!response.ok) throw new Error("Не вдалося завантажити подорожі.");
          const body = await response.json();
          list.replaceChildren();
          dashboardList.replaceChildren();
          const jobs = body.jobs;
          document.querySelector("#trip-count").textContent = String(jobs.length);
          document.querySelector("#active-count").textContent = String(jobs.filter((job) =>
            ["queued", "preparing", "generating", "validating", "cancel_requested"].includes(job.status)
          ).length);
          document.querySelector("#last-trip-destination").textContent =
            jobs.length ? jobs[0].destination || "Подорож" : "Ще не обрано";
          const remainder = jobs.length % 10;
          const lastTwoDigits = jobs.length % 100;
          const tripWord = remainder === 1 && lastTwoDigits !== 11
            ? "подорож"
            : remainder >= 2 && remainder <= 4 && (lastTwoDigits < 12 || lastTwoDigits > 14)
              ? "подорожі"
              : "подорожей";
          document.querySelector("#trips-summary").textContent = `${jobs.length} ${tripWord}`;
          dashboardEmpty.hidden = jobs.length !== 0;
          if (!body.jobs.length) {
            const empty = document.createElement("p");
            empty.className = "hint";
            empty.textContent = "Поки що збережених подорожей немає.";
            list.append(empty);
            return;
          }
          jobs.forEach((job) => list.append(createTripRow(job)));
          jobs.slice(0, 3).forEach((job) => dashboardList.append(createTripCard(job)));
        } catch {
          const message = document.createElement("p");
          message.className = "notice error";
          message.textContent = "Не вдалося завантажити подорожі. Перевірте з’єднання та спробуйте оновити сторінку.";
          list.replaceChildren(message.cloneNode(true));
          dashboardList.replaceChildren(message);
          dashboardEmpty.hidden = true;
          document.querySelector("#trips-summary").textContent = "Не вдалося завантажити список.";
        }
      }

      function stopJobUpdates() {
        if (activeEventSource) activeEventSource.close();
        activeEventSource = null;
        if (statusPollTimer) clearInterval(statusPollTimer);
        statusPollTimer = null;
      }

      function renderJob(job) {
        const panel = document.querySelector("#job-progress");
        activeJobId = job.id;
        panel.hidden = false;
        panel.dataset.state = job.status;
        document.querySelector("#detail-title").textContent = job.destination || "Подорож";
        document.querySelector("#detail-dates").textContent = formattedTripDates(job);
        const providerMode = job.provider_mode || "mock";
        const providerPill = document.querySelector("#detail-provider-mode");
        providerPill.textContent = providerMode === "mock" ? "Генератор: mock" : "Генератор: OpenAI";
        providerPill.dataset.status = providerMode === "mock" ? "queued" : "completed";
        const statusPill = document.querySelector("#detail-status");
        statusPill.dataset.status = job.status;
        statusPill.textContent = statusLabel(job.status);
        document.querySelector("#job-message").textContent = job.message;
        renderProgressState(job.status);
        const terminal = ["completed", "failed", "cancelled", "interrupted"].includes(job.status);
        document.querySelector("#job-progress-bar").hidden = terminal;
        const cancelButton = document.querySelector("#cancel-job");
        cancelButton.hidden = terminal;
        cancelButton.disabled = job.status === "cancel_requested";
        const target = document.querySelector("#job-result");
        target.replaceChildren();
        if (job.status === "completed" && job.plan) displayPlan(job.plan, target);
        if (job.status === "interrupted") {
          const note = document.createElement("p");
          note.className = "notice error";
          note.textContent = "Задача перервалася під час обробки. Створіть новий запит, щоб повторити її.";
          target.append(note);
        }
        if (terminal) {
          stopJobUpdates();
          sessionStorage.removeItem("tripplanner:activeJobId");
          loadTrips();
        }
      }

      function renderProgressState(status) {
        const stages = ["queued", "preparing", "generating", "validating", "completed"];
        const currentIndex = stages.indexOf(status);
        document.querySelectorAll("#progress-steps [data-stage]").forEach((item, index) => {
          item.removeAttribute("data-step-state");
          if (currentIndex >= 0 && index < currentIndex) item.dataset.stepState = "done";
          if (currentIndex >= 0 && index === currentIndex) item.dataset.stepState = "current";
        });
      }

      async function pollJob(jobId) {
        try {
          const response = await apiFetch(`/api/v1/jobs/${encodeURIComponent(jobId)}`);
          if (response.status === 401) {
            stopJobUpdates();
            requireLogin("Сеанс завершився. Увійдіть знову.");
            return;
          }
          if (response.status === 404) {
            stopJobUpdates();
            sessionStorage.removeItem("tripplanner:activeJobId");
            const panel = document.querySelector("#job-progress");
            panel.hidden = false;
            panel.dataset.state = "interrupted";
            document.querySelector("#detail-title").textContent = "Подорож недоступна";
            document.querySelector("#detail-dates").textContent = "";
            const statusPill = document.querySelector("#detail-status");
            statusPill.dataset.status = "interrupted";
            statusPill.textContent = "Не знайдено";
            document.querySelector("#job-message").textContent =
              "Не знайшли цю задачу. У локальному режимі пам’ять очищається після перезапуску сервера.";
            document.querySelector("#job-progress-bar").hidden = true;
            document.querySelector("#cancel-job").hidden = true;
            renderProgressState("interrupted");
            return null;
          }
          if (!response.ok) throw new Error("Не вдалося отримати стан подорожі.");
          const job = (await response.json()).job;
          renderJob(job);
          return job;
        } catch {
          document.querySelector("#job-message").textContent =
            "Не вдалося оновити стан. Перевірте з’єднання — повторна перевірка триває.";
          return null;
        }
      }

      async function openJob(jobId, initialJob = null) {
        stopJobUpdates();
        activeJobId = jobId;
        sessionStorage.setItem("tripplanner:activeJobId", jobId);
        const job = initialJob
          ? initialJob
          : await pollJob(jobId);
        if (initialJob && job) renderJob(job);
        if (!job) return false;
        if (["completed", "failed", "cancelled", "interrupted"].includes(job.status)) return true;
        if (!initialJob) renderJob(job);
        const url = `/api/v1/jobs/${encodeURIComponent(jobId)}/events?after_id=${encodeURIComponent(job.latest_event_id)}`;
        activeEventSource = new EventSource(url);
        activeEventSource.addEventListener("progress", async (event) => {
          const update = JSON.parse(event.data);
          document.querySelector("#job-message").textContent = update.message;
          const statusPill = document.querySelector("#detail-status");
          statusPill.dataset.status = update.status;
          statusPill.textContent = statusLabel(update.status);
          renderProgressState(update.status);
          const terminal = ["completed", "failed", "cancelled", "interrupted"].includes(update.status);
          document.querySelector("#job-progress-bar").hidden = terminal;
          document.querySelector("#cancel-job").hidden = terminal;
          document.querySelector("#cancel-job").disabled = update.status === "cancel_requested";
          if (["completed", "failed", "cancelled", "interrupted"].includes(update.status)) {
            await pollJob(jobId);
          } else {
            const progressPanel = document.querySelector("#job-progress");
            progressPanel.dataset.state = update.status;
          }
        });
        activeEventSource.onopen = () => {
          if (statusPollTimer) clearInterval(statusPollTimer);
          statusPollTimer = null;
        };
        activeEventSource.onerror = () => {
          if (!statusPollTimer) {
            document.querySelector("#job-message").textContent =
              "З’єднання перервано. Відновлюємо його та перевіряємо стан задачі…";
            statusPollTimer = setInterval(() => { pollJob(jobId); }, 5000);
          }
        };
        return true;
      }

      async function restoreLastJob() {
        let route = renderRoute();
        if (route.page === "detail") {
          await openJob(route.jobId);
          return;
        }
        const savedJobId = sessionStorage.getItem("tripplanner:activeJobId");
        let jobId = savedJobId;
        if (jobId) {
          const savedJob = await pollJob(jobId);
          if (!savedJob || ["completed", "failed", "cancelled", "interrupted"].includes(savedJob.status)) {
            jobId = null;
          }
        }
        if (!jobId) {
          try {
            const response = await apiFetch("/api/v1/jobs");
            if (!response.ok) return;
            const body = await response.json();
            const active = body.jobs.find((job) =>
              ["queued", "preparing", "generating", "validating", "cancel_requested"].includes(job.status)
            );
            jobId = active?.id || null;
          } catch {
            return;
          }
        }
        if (jobId) {
          await navigateTo(`/trips/${encodeURIComponent(jobId)}`, true);
        }
      }

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

      function createLiveCardTitle(text) {
        const title = document.createElement("h3");
        title.textContent = text;
        return title;
      }

      function createLivePlaceList(places) {
        const list = document.createElement("ul");
        if (!places || !places.length) {
          const item = document.createElement("li");
          item.textContent = "Відкритих даних не знайдено поблизу.";
          list.append(item);
          return list;
        }
        for (const place of places.slice(0, 5)) {
          const item = document.createElement("li");
          const name = document.createElement("strong");
          name.textContent = place.name;
          item.append(name);
          if (place.address) item.append(document.createTextNode(place.address));
          list.append(item);
        }
        return list;
      }

      function displayPlan(plan, target) {
        const title = document.createElement("h2");
        title.textContent = `Ваш план подорожі: ${plan.destination}`;
        target.replaceChildren(title);

        const badges = document.createElement("div");
        badges.className = "badges";
        const sourceNames = {
          main: "Результат OpenAI-сумісної AI-моделі",
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

        if (plan.live_info) {
          const live = plan.live_info;
          const liveInfo = document.createElement("section");
          liveInfo.className = "live-info";
          liveInfo.setAttribute("aria-label", "Актуальна довідкова інформація");

          const weatherCard = document.createElement("article");
          weatherCard.className = "live-card";
          const weatherTitle = document.createElement("h3");
          weatherTitle.textContent = "☁ Погода";
          weatherCard.append(weatherTitle);
          const weatherList = document.createElement("ul");
          if (live.weather && live.weather.length) {
            for (const day of live.weather) {
              const item = document.createElement("li");
              const temperature = day.temperature_min !== null && day.temperature_max !== null
                ? `${day.temperature_min}–${day.temperature_max}°C`
                : "Температура уточнюється";
              const rain = day.precipitation_probability !== null
                ? ` · ймовірність опадів ${day.precipitation_probability}%`
                : "";
              item.innerHTML = `<strong>${day.date}</strong>${temperature}${rain}`;
              weatherList.append(item);
            }
          } else {
            const item = document.createElement("li");
            item.textContent = "Прогноз недоступний для цих дат. Перевірте погоду перед виїздом.";
            weatherList.append(item);
          }
          weatherCard.append(weatherList);

          const attractionsCard = document.createElement("article");
          attractionsCard.className = "live-card";
          attractionsCard.append(createLiveCardTitle("↗ Цікаві місця"));
          attractionsCard.append(createLivePlaceList(live.attractions));

          const stayCard = document.createElement("article");
          stayCard.className = "live-card";
          stayCard.append(createLiveCardTitle("⌂ Де переночувати"));
          stayCard.append(createLivePlaceList(live.accommodations));

          liveInfo.append(weatherCard, attractionsCard, stayCard);
          if (live.sources && live.sources.length) {
            const source = document.createElement("p");
            source.className = "live-source";
            source.textContent = `Джерела: ${live.sources.join(", ")}. Дані довідкові; ціни, час роботи й наявність не підтверджено.`;
            liveInfo.append(source);
          }
          target.append(liveInfo);
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
        const newPlan = document.createElement("a");
        newPlan.className = "button secondary small";
        newPlan.href = "/new";
        newPlan.dataset.nav = "";
        newPlan.textContent = "Створити інший план";
        target.append(newPlan);
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
        const payload = requestPayload();
        setStatus("Надсилаємо запит до черги…");
        try {
          const providerSettings = await loadProviderSettings();
          if (!providerSettings) {
            setStatus("Не вдалося перевірити глобальний режим AI. Перевірте з’єднання та спробуйте ще раз.", true);
            return;
          }
          const response = await apiFetch("/api/v1/jobs", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Idempotency-Key": getIdempotencyKey(payload)
            },
            body: JSON.stringify(payload)
          });
          const body = await response.json();
          if (!response.ok) {
            const error = body.error || {};
            const requestInfo = error.request_id ? ` Номер запиту: ${error.request_id}.` : "";
            if (response.status === 401) {
              requireLogin("Сеанс завершився. Увійдіть знову.");
              return;
            }
            if (response.status === 422 && Array.isArray(error.fields)) {
              showServerFieldErrors(error.fields);
              setStatus(`Сервер відхилив введені дані. Перевірте позначені поля.${requestInfo}`, true);
            } else if (error.retryable) {
              const retryAfter = Number(response.headers.get("Retry-After") || error.retry_after || 0);
              setStatus(`Тимчасова помилка. ${retryAfter > 0 ? `Спробуйте через ${retryAfter} с.` : "Спробуйте ще раз."}${requestInfo}`, true);
            } else {
              if (error.code === "idempotency_conflict") {
                pendingSubmission = null;
                sessionStorage.removeItem("tripplanner:pendingSubmission");
              }
              const errorMessages = {
                rate_limited: "Забагато запитів. Спробуйте пізніше.",
                daily_budget_exceeded: "Денний ліміт витрат на AI вичерпано.",
                provider_unavailable: "Сервіс планування тимчасово недоступний.",
                provider_timeout: "Час очікування відповіді сервісу вичерпано.",
                invalid_output: "Сервіс планування повернув некоректний результат.",
                idempotency_conflict: "Ключ запиту вже використано з іншими даними. Натисніть «Створити план» ще раз.",
                not_found: "План не знайдено.",
                unauthorized: "Сеанс завершився. Увійдіть знову.",
                internal: "Сталася неочікувана помилка."
              };
              setStatus(`${errorMessages[error.code] || "Не вдалося створити план."}${requestInfo}`, true);
            }
            return;
          }
          sessionStorage.removeItem("tripplanner:pendingSubmission");
          pendingSubmission = null;
          setStatus(body.created
            ? "Запит прийнято. Відкриваємо сторінку подорожі."
            : "Цей запит уже обробляється або виконаний. Відновлюємо його стан.");
          await navigateTo(`/trips/${encodeURIComponent(body.job.id)}`);
        } catch {
          const reachable = await checkService();
          if (reachable) {
            setStatus("Сервер відповідає, але передавання запиту перервалося. Перевірте «Мої подорожі» перед повтором; однаковий запит не створить дублікат.", true);
          } else {
            setStatus(`Сервер за адресою ${window.location.origin} не відповідає. Запустіть застосунок і повторіть спробу.`, true);
          }
        } finally {
          createButton.disabled = false;
        }
      });

      document.querySelector("#login-form").addEventListener("submit", (event) => {
        event.preventDefault();
        authenticate();
      });
      document.querySelector("#register-form").addEventListener("submit", (event) => {
        event.preventDefault();
        registerAccount();
      });
      document.querySelector("#register-password-confirm").addEventListener("input", (event) => {
        event.target.setCustomValidity(
          event.target.value === document.querySelector("#register-password").value
            ? ""
            : "Паролі не збігаються."
        );
      });
      document.querySelector("#verify-button").addEventListener("click", verifyEmail);
      document.querySelector("#resend-form").addEventListener("submit", resendVerification);
      document.querySelector("#provider-mode").addEventListener("change", (event) => {
        document.querySelector("#save-provider-mode").disabled =
          event.target.value === currentProviderMode;
      });
      document.querySelector("#save-provider-mode").addEventListener("click", async () => {
        const button = document.querySelector("#save-provider-mode");
        const message = document.querySelector("#provider-settings-status");
        button.disabled = true;
        message.textContent = "Зберігаємо глобальний режим…";
        try {
          const response = await apiFetch("/api/v1/settings/provider", {
            method: "PUT",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({mode: document.querySelector("#provider-mode").value})
          });
          const body = await response.json();
          if (!response.ok) {
            const errors = {
              provider_unavailable: "OpenAI API ще не налаштований. Додайте серверний ключ і ціни токенів у .env.",
              not_found: "Змінювати глобальний режим може лише адміністратор."
            };
            throw new Error(errors[body.error?.code] || body.error?.message || "Не вдалося зберегти режим.");
          }
          await loadProviderSettings();
          await checkService();
          message.textContent = "Глобальний режим збережено. Нові завдання використовуватимуть його; уже створені не змінюються.";
        } catch (error) {
          message.textContent = error instanceof Error
            ? error.message
            : "Не вдалося зберегти режим AI.";
          button.disabled = false;
        }
      });
      document.querySelector("#logout-button").addEventListener("click", async () => {
        try {
          const response = await apiFetch("/api/v1/auth/logout", {method: "POST"});
          if (!response.ok) throw new Error("Не вдалося завершити сеанс.");
          sessionStorage.removeItem("tripplanner:activeJobId");
          requireLogin("Ви вийшли з облікового запису.");
        } catch {
          showAuthMessage("Не вдалося завершити сеанс. Перевірте з’єднання й повторіть спробу.", true);
        }
      });
      document.querySelector("#cancel-job").addEventListener("click", async () => {
        if (!activeJobId) return;
        const button = document.querySelector("#cancel-job");
        button.disabled = true;
        try {
          const response = await apiFetch(`/api/v1/jobs/${encodeURIComponent(activeJobId)}/cancel`, {
            method: "POST"
          });
          if (!response.ok) throw new Error("Не вдалося скасувати завдання.");
          const job = (await response.json()).job;
          renderJob(job);
        } catch {
          button.disabled = false;
          document.querySelector("#job-message").textContent =
            "Не вдалося надіслати скасування. Перевірте з’єднання й повторіть спробу.";
        }
      });

      async function checkService() {
        const checkButton = document.querySelector("#check-service");
        const aiModeNote = document.querySelector("#ai-mode-note");
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), 3000);
        checkButton.disabled = true;
        try {
          const response = await fetch("/health", {cache: "no-store", signal: controller.signal});
          if (!response.ok) throw new Error("Не вдалося перевірити доступність сервісу.");
          const health = await response.json();
          serviceState.dataset.state = "ok";
          const providerNames = {mock: "демонстраційний генератор", openai_compat: "OpenAI-сумісний AI-провайдер"};
          if (health.checks.ai_mode === "demo") {
            serviceState.textContent = "Сервер доступний. План створює демонстраційний генератор, не зовнішня AI-модель.";
            aiModeNote.textContent = "Для реальної генерації потрібні AI-провайдер, API-ключ і ціни токенів у локальному файлі .env.";
          } else {
            const model = health.checks.model ? ` (${health.checks.model})` : "";
            serviceState.textContent = `Сервер доступний. Вибрано ${providerNames[health.checks.provider] || "AI-провайдер"}${model}.`;
            aiModeNote.textContent = "Після створення плану сервер надсилає дані запиту провайдеру; доступність моделі перевіряється під час генерації.";
          }
          if (health.checks.storage === "memory") {
            aiModeNote.textContent += " Історія в режимі memory очищується після перезапуску сервера.";
          }
          return true;
        } catch {
          serviceState.dataset.state = "error";
          serviceState.textContent = `Сервер ${window.location.origin} недоступний. Запустіть його в терміналі та оновіть сторінку.`;
          aiModeNote.textContent = "Форма не може надіслати запит, доки сервер не відповідає.";
          return false;
        } finally {
          window.clearTimeout(timeout);
          checkButton.disabled = false;
        }
      }

      document.querySelector("#check-service").addEventListener("click", checkService);
      checkService();
      restoreSession();
    </script>
  </body>
</html>
"""


def index_page() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)

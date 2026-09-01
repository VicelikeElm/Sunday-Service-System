(() => {
  "use strict";

  const ENDPOINT = "http://127.0.0.1:8765/sermon-plan";
  const PLAN_ID_KEY = "sermon-ai-last-plan-id";
  const POLL_MS = 3000;

  function clean(value) {
    return String(value ?? "").trim();
  }

  function setLocal(key, value) {
    localStorage.setItem(key, clean(value));
  }

  function applyPlan(plan) {
    const title = clean(plan.title);
    const scripture = clean(plan.scripture);
    const preacher = clean(plan.preacher);
    const points = Array.isArray(plan.points)
      ? plan.points.map(clean).filter(Boolean)
      : [];

    if (!title || !scripture || points.length === 0) {
      console.warn("[SermonAI] Sermon plan is incomplete; not applying.");
      return false;
    }

    // LT1 follows the existing church pattern:
    // active = point 1 + Scripture
    // slots 1..N = each sermon point + Scripture
    setLocal("alt-1-name", points[0]);
    setLocal("alt-1-info", scripture);

    points.slice(0, 10).forEach((point, index) => {
      const slot = index + 1;
      setLocal(`alt-1-name-${slot}`, point);
      setLocal(`alt-1-info-${slot}`, scripture);
    });

    // LT2 follows the existing title pattern.
    setLocal("alt-2-name", title);
    setLocal("alt-2-info", scripture);

    setLocal("alt-2-name-1", title);
    setLocal("alt-2-info-1", scripture);

    if (preacher) {
      setLocal("alt-2-name-2", title);
      setLocal("alt-2-info-2", preacher);
    }

    return true;
  }

  async function checkPlan() {
    try {
      const response = await fetch(
        ENDPOINT,
        { cache: "no-store" }
      );

      if (!response.ok) {
        return;
      }

      const plan = await response.json();

      if (!plan.ok) {
        return;
      }

      const planId = clean(
        plan.plan_id ||
        plan.updated ||
        `${plan.title}|${plan.scripture}|${(plan.points || []).join("|")}`
      );

      if (!planId) {
        return;
      }

      const previous = localStorage.getItem(
        PLAN_ID_KEY
      );

      if (previous === planId) {
        return;
      }

      if (applyPlan(plan)) {
        localStorage.setItem(
          PLAN_ID_KEY,
          planId
        );

        console.log(
          "[SermonAI] Loaded this week's sermon into LT1/LT2."
        );

        // Reload once so the existing control panel redraws itself
        // from its own localStorage values.
        setTimeout(() => {
          window.location.reload();
        }, 250);
      }
    } catch (error) {
      // Sunday Mode may not be running. Stay quiet and retry later.
    }
  }

  window.addEventListener(
    "DOMContentLoaded",
    () => {
      checkPlan();
      setInterval(
        checkPlan,
        POLL_MS
      );
    }
  );
})();

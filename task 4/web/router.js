const ROUTES = Object.freeze({
  intro: "/gioi-thieu",
  candidate: "/thong-tin-ung-vien",
  interview: "/phong-van",
});

const SCREEN_BY_PATH = new Map(
  Object.entries(ROUTES).map(([screen, route]) => [route, screen])
);

function screenFromLocation() {
  const path = window.location.hash.slice(1).replace(/\/$/, "") || ROUTES.intro;
  return SCREEN_BY_PATH.get(path) || "intro";
}

export function createRouter({ canEnter = () => true, onChange }) {
  if (typeof onChange !== "function") {
    throw new TypeError("Router requires an onChange callback");
  }

  function renderLocation() {
    const requestedScreen = screenFromLocation();
    const screen = canEnter(requestedScreen) ? requestedScreen : "candidate";
    const expectedHash = `#${ROUTES[screen]}`;

    if (window.location.hash !== expectedHash) {
      window.history.replaceState(null, "", expectedHash);
    }

    onChange(screen);
  }

  function navigate(screen, { replace = false } = {}) {
    if (!(screen in ROUTES)) {
      throw new Error(`Unknown screen: ${screen}`);
    }

    const destination = canEnter(screen) ? screen : "candidate";
    const nextHash = `#${ROUTES[destination]}`;

    if (window.location.hash === nextHash || replace) {
      window.history.replaceState(null, "", nextHash);
      onChange(destination);
      return;
    }

    window.location.hash = ROUTES[destination];
  }

  function start() {
    window.addEventListener("hashchange", renderLocation);
    renderLocation();
  }

  return { navigate, start };
}

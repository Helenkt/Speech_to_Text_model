const ROUTES = Object.freeze({
  login: "/dang-nhap",
  intro: "/gioi-thieu",
  profile: "/thong-tin-ca-nhan",
  interview: "/phong-van",
});

const SCREEN_BY_PATH = new Map(
  Object.entries(ROUTES).map(([screen, route]) => [route, screen])
);

function screenFromLocation() {
  const path = window.location.hash.slice(1).replace(/\/$/, "") || ROUTES.login;
  return SCREEN_BY_PATH.get(path) || "login";
}

export function createRouter({ resolveScreen = (screen) => screen, onChange }) {
  if (typeof onChange !== "function") {
    throw new TypeError("Router requires an onChange callback");
  }

  function renderLocation() {
    const requestedScreen = screenFromLocation();
    const screen = resolveScreen(requestedScreen);
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

    const destination = resolveScreen(screen);
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

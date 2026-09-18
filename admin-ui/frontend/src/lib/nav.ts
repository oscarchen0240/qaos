export const NAV_REFRESH_EVENT = "nav:refresh";

export function refreshNav() {
  window.dispatchEvent(new Event(NAV_REFRESH_EVENT));
}

export const createObjectUrl = () => {
  let active = true;
  const urls = new Set<string>();
  const setUrl = (url: string | null | undefined, onReady: (url: string) => void) => {
    if (!url) return;
    if (!active) {
      if (url.startsWith("blob:")) URL.revokeObjectURL(url);
      return;
    }
    urls.add(url);
    onReady(url);
  };
  const cleanup = () => {
    active = false;
    urls.forEach((u) => {
      if (u.startsWith("blob:")) URL.revokeObjectURL(u);
    });
    urls.clear();
  };
  return { setUrl, cleanup };
};

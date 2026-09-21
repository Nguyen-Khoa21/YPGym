type BackRouter<T> = {
  back: () => void;
  canGoBack: () => boolean;
  replace: (path: T) => void;
};

export function goBackOrReplace<T>(router: BackRouter<T>, fallback: T) {
  if (router.canGoBack()) router.back();
  else router.replace(fallback);
}

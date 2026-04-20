import { registerRoot } from "remotion";
import { RemotionRoot } from "./Root";
import { waitUntilDone } from "./fonts";

waitUntilDone().then(() => {
  registerRoot(RemotionRoot);
});

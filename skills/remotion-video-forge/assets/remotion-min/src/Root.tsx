import { Composition } from "remotion";
import { Video } from "./Video";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="MyVideo"
    component={Video}
    durationInFrames={150}
    fps={30}
    width={1920}
    height={1080}
    defaultProps={{ title: "未命名 · 用代码做视频" }}
  />
);

import { fileURLToPath } from "node:url";
import { startPortal } from "../web-shared/server.mjs";
startPortal({ root: fileURLToPath(new URL(".", import.meta.url)), defaultPort: 4174, name: "Management Portal", roles: ["STAFF", "ADMIN"] });

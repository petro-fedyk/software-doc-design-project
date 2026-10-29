import { fileURLToPath } from "node:url";
import { startPortal } from "../web-shared/server.mjs";
startPortal({ root: fileURLToPath(new URL(".", import.meta.url)), defaultPort: 4173, name: "Customer Portal", roles: ["CUSTOMER"] });

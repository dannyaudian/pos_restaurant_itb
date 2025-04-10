// continue.config.ts
import { ContinueConfig } from "continue";

const config: ContinueConfig = {
  project: {
    name: "POS Restaurant ITB",
    root: "./pos_restaurant_itb", // folder app Frappe-nya
    fileTypes: ["py", "js", "json", "md"],

    folders: [
      "api",
      "utils",
      "custom"
    ],

    exclude: ["__pycache__", "node_modules", ".git"]
  },

  indexing: {
    includeGlobs: ["**/*.py", "**/*.js", "**/*.json", "**/*.md"],
    excludeGlobs: ["**/__pycache__/**", "**/*.pyc"]
  }
};

export default config;

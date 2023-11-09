import type { Config } from "@jest/types";
import { pathsToModuleNameMapper } from "ts-jest";
// Load the config which holds the path aliases.
import { compilerOptions } from "../../tsconfig.json";

const config: Config.InitialOptions = {
  preset: "ts-jest",
  testTimeout: 60000,
  moduleNameMapper: pathsToModuleNameMapper(compilerOptions.paths, {
    // This has to match the baseUrl defined in tsconfig.json.
    prefix: "<rootDir>/../../",
  }),
};

export default config;

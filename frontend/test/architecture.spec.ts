import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, extname, join, normalize, relative, resolve } from "node:path";
import ts from "typescript";
import { describe, expect, it } from "vitest";

const frontendRoot = resolve(__dirname, "..");
const sourceRoots = [join(frontendRoot, "app"), join(frontendRoot, "src")];
const supportedSourceExtensions = new Set([".ts", ".tsx"]);
const resolvableExtensions = [".ts", ".tsx", ".js", ".jsx", ".css"];
const layerOrder = {
  shared: 0,
  entities: 1,
  features: 2,
  widgets: 3,
  app: 4
} as const;

type LayerName = keyof typeof layerOrder;

describe("frontend architecture", () => {
  it("enforces app -> widgets -> features -> entities -> shared imports", () => {
    const violations: string[] = [];

    for (const filePath of collectSourceFiles()) {
      const sourceLayer = getLayerForPath(filePath);
      if (!sourceLayer) {
        continue;
      }

      for (const specifier of collectImportSpecifiers(filePath)) {
        const resolved = resolveLocalImport(filePath, specifier);
        if (!resolved) {
          continue;
        }

        const targetLayer = getLayerForPath(resolved);
        if (!targetLayer) {
          continue;
        }

        if (layerOrder[targetLayer] > layerOrder[sourceLayer]) {
          violations.push(
            `${toRelativePath(filePath)} -> ${specifier} (${sourceLayer} -> ${targetLayer})`
          );
        }
      }
    }

    expect(violations).toEqual([]);
  });
});

function collectSourceFiles(): string[] {
  return sourceRoots.flatMap((root) => walkDirectory(root)).filter((filePath) =>
    supportedSourceExtensions.has(extname(filePath))
  );
}

function walkDirectory(directory: string): string[] {
  const entries = readdirSync(directory, { withFileTypes: true });
  const files: string[] = [];

  for (const entry of entries) {
    const fullPath = join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...walkDirectory(fullPath));
      continue;
    }
    files.push(fullPath);
  }

  return files;
}

function collectImportSpecifiers(filePath: string): string[] {
  const sourceText = readFileSync(filePath, "utf-8");
  const sourceFile = ts.createSourceFile(filePath, sourceText, ts.ScriptTarget.Latest, true);
  const specifiers = new Set<string>();

  const visit = (node: ts.Node) => {
    if (
      (ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) &&
      node.moduleSpecifier &&
      ts.isStringLiteral(node.moduleSpecifier)
    ) {
      specifiers.add(node.moduleSpecifier.text);
    }

    if (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword) {
      const [firstArgument] = node.arguments;
      if (firstArgument && ts.isStringLiteral(firstArgument)) {
        specifiers.add(firstArgument.text);
      }
    }

    ts.forEachChild(node, visit);
  };

  visit(sourceFile);
  return [...specifiers];
}

function resolveLocalImport(fromFile: string, specifier: string): string | null {
  if (specifier.startsWith("@/")) {
    return resolveProjectPath(join(frontendRoot, specifier.slice(2)));
  }

  if (specifier.startsWith(".")) {
    return resolveProjectPath(resolve(dirname(fromFile), specifier));
  }

  return null;
}

function resolveProjectPath(candidatePath: string): string | null {
  const normalizedPath = normalize(candidatePath);

  if (existsSync(normalizedPath) && statSync(normalizedPath).isFile()) {
    return normalizedPath;
  }

  for (const extension of resolvableExtensions) {
    const withExtension = `${normalizedPath}${extension}`;
    if (existsSync(withExtension) && statSync(withExtension).isFile()) {
      return normalize(withExtension);
    }
  }

  for (const extension of resolvableExtensions) {
    const indexPath = join(normalizedPath, `index${extension}`);
    if (existsSync(indexPath) && statSync(indexPath).isFile()) {
      return normalize(indexPath);
    }
  }

  return null;
}

function getLayerForPath(filePath: string): LayerName | null {
  const relativePath = toRelativePath(filePath);

  if (relativePath.startsWith("app/")) {
    return "app";
  }
  if (relativePath.startsWith("src/widgets/")) {
    return "widgets";
  }
  if (relativePath.startsWith("src/features/")) {
    return "features";
  }
  if (relativePath.startsWith("src/entities/")) {
    return "entities";
  }
  if (relativePath.startsWith("src/shared/")) {
    return "shared";
  }

  return null;
}

function toRelativePath(filePath: string): string {
  return relative(frontendRoot, filePath).replaceAll("\\", "/");
}

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const failures = [];
const checks = [];

function pass(label) {
  checks.push(label);
}

function fail(label, detail) {
  failures.push(`${label}: ${detail}`);
}

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

function expectFile(relativePath) {
  if (!fs.existsSync(path.join(root, relativePath))) {
    fail("required file", `${relativePath} is missing`);
  }
}

const requiredFiles = [
  "index.html",
  "package.json",
  "tsconfig.json",
  "src/main.tsx",
  "src/app/App.tsx",
  "src/app/AppShell.tsx",
  "src/auth/AuthProvider.tsx",
  "src/api/client.ts",
  "src/pages/HomePage.tsx",
  "src/pages/PolicyPage.tsx",
  "src/pages/ReportsPage.tsx",
  "src/pages/ReportWorkspacePage.tsx",
  "src/pages/PolicyLibraryPage.tsx",
  "src/pages/SavedPage.tsx",
  "src/pages/AccountPage.tsx",
  "src/admin/AdminPages.tsx",
  "src/styles/global.css",
];
requiredFiles.forEach(expectFile);
if (!failures.length) pass("required application files are present");

for (const relativePath of ["package.json", "tsconfig.json"]) {
  try {
    JSON.parse(read(relativePath));
    pass(`${relativePath} is valid JSON`);
  } catch (error) {
    fail("JSON parse", `${relativePath}: ${error.message}`);
  }
}

const sourceFiles = [];
function walk(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) walk(absolute);
    else if (/\.(?:ts|tsx)$/.test(entry.name) && !entry.name.endsWith(".test.tsx")) {
      sourceFiles.push(absolute);
    }
  }
}
walk(path.join(root, "src"));
const applicationSource = sourceFiles.map((file) => fs.readFileSync(file, "utf8")).join("\n");

const forbiddenPersistence = ["localStorage", "sessionStorage", "indexedDB", "serviceWorker"];
for (const token of forbiddenPersistence) {
  if (applicationSource.includes(token)) fail("browser persistence boundary", `${token} appears in application source`);
}
if (!forbiddenPersistence.some((token) => applicationSource.includes(token))) {
  pass("application source does not use offline browser persistence");
}

for (const token of ["access_token", "renewal_token", "dangerouslySetInnerHTML"]) {
  if (applicationSource.includes(token)) fail("sensitive client boundary", `${token} appears in application source`);
}
if (!["access_token", "renewal_token", "dangerouslySetInnerHTML"].some((token) => applicationSource.includes(token))) {
  pass("application source does not expose tokens or raw HTML injection");
}

const apiClient = read("src/api/client.ts");
for (const required of ['credentials: "same-origin"', 'cache: "no-store"', 'headers.set("X-CSRF-Token"']) {
  if (!apiClient.includes(required)) fail("API client security", `missing ${required}`);
}
if (failures.every((item) => !item.startsWith("API client security"))) {
  pass("API client enforces same-origin cookies, no-store requests, and CSRF headers");
}

const routes = read("src/app/App.tsx");
for (const requiredRoute of [
  'path="/sign-in"',
  'path="/change-pin"',
  'path="policy"',
  'path="reports"',
  'path="reports/new"',
  'path="library"',
  'path="saved"',
  'path="account"',
  'path="admin"',
]) {
  if (!routes.includes(requiredRoute)) fail("route coverage", `missing ${requiredRoute}`);
}
if (failures.every((item) => !item.startsWith("route coverage"))) pass("core Officer and Administrator routes are declared");

if (!applicationSource.includes("No report was saved")) {
  fail("live failure behavior", "new live reports do not explicitly refuse an unconnected create adapter");
}
if (!applicationSource.includes("no report content is displayed")) {
  fail("live failure behavior", "failed report loads do not explicitly suppress fallback content");
}
if (failures.every((item) => !item.startsWith("live failure behavior"))) {
  pass("live report failures do not substitute fictional success or content");
}

const liveAdminGuards = applicationSource.match(/if \(!designPreviewEnabled\)/g)?.length ?? 0;
if (liveAdminGuards < 5) fail("preview isolation", `expected at least 5 live Admin guards; found ${liveAdminGuards}`);
else pass("Administrator preview records are guarded from live mode");

const allText = [applicationSource, read("README.md")].join("\n").toLowerCase();
if (allText.includes("shift notes")) fail("product terminology", 'use "field notes," not "shift notes"');
else pass('product copy consistently uses "field notes"');

const cssFiles = fs.readdirSync(path.join(root, "src/styles")).filter((name) => name.endsWith(".css"));
const css = cssFiles.map((name) => read(`src/styles/${name}`)).join("\n");
for (const required of [":focus-visible", "@media (max-width: 860px)", "@media (max-width: 640px)", "@media (prefers-reduced-motion: reduce)"]) {
  if (!css.includes(required)) fail("accessible responsive styles", `missing ${required}`);
}
if (failures.every((item) => !item.startsWith("accessible responsive styles"))) {
  pass("styles include keyboard focus, responsive breakpoints, and reduced-motion handling");
}

for (const file of [...sourceFiles, ...cssFiles.map((name) => path.join(root, "src/styles", name))]) {
  const text = fs.readFileSync(file, "utf8");
  if (!text.endsWith("\n")) fail("file hygiene", `${path.relative(root, file)} does not end with a newline`);
}
if (failures.every((item) => !item.startsWith("file hygiene"))) pass("checked source files end with a newline");

for (const label of checks) console.log(`PASS  ${label}`);
if (failures.length) {
  for (const item of failures) console.error(`FAIL  ${item}`);
  console.error(`\n${failures.length} foundation validation failure(s).`);
  process.exit(1);
}
console.log(`\n${checks.length} foundation checks passed.`);

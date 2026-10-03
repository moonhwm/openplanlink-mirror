#!/usr/bin/env node
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { buildManifest, decodeKey, verifyManifest } from "./sha3-tree.mjs";

const key = Buffer.alloc(64, 0x42);
const keyId = "test-domain-2026q4";
const generatedAt = "2026-10-03T00:00:00.000Z";
const files = [
  { path: "alpha.txt", bytes: Buffer.from("alpha\n") },
  { path: "nested/beta.txt", bytes: Buffer.from("beta\r\n") },
  { path: "中文.txt", bytes: Buffer.from("原始字节\n") },
];
const expectedRoot = "c2ab85ffee21698774a5c2e0f09b68eaa47310f2adebd01ae4e5b694782eec365da59f7e533a793ca71eb88f720631ea713c39f5f14d57017ae7c9134451f7f5";
const expectedTag = "d3b8873850cb3fac91c650b0b0ba19bb8ef084162da05f6a4f1447b51985643418b3484a3c4028a8a84582a5dc2e4bb511d0a2d0d48c85876d7e5ec276c45965";

const manifest = buildManifest(files, key, keyId, generatedAt);
const reordered = buildManifest([...files].reverse(), key, keyId, generatedAt);
assert.equal(manifest.merkle_root_sha3_512, expectedRoot);
assert.equal(manifest.hmac_sha3_512, expectedTag);
assert.equal(reordered.merkle_root_sha3_512, expectedRoot);
assert.equal(reordered.hmac_sha3_512, expectedTag);
assert.equal(manifest.file_count, 3);
assert.equal(verifyManifest(manifest, files, key, keyId), true);
assert.throws(
  () => verifyManifest(manifest, files, Buffer.alloc(64, 0x43), keyId),
  /verification failed/,
);
assert.throws(() => verifyManifest(manifest, files, key, "wrong-key-id"), /key_id mismatch/);
assert.throws(() => decodeKey("not-base64"), /canonical base64/);
assert.throws(
  () => buildManifest([{ path: "../escape", bytes: Buffer.alloc(0) }], key, keyId, generatedAt),
  /unsafe path/,
);
assert.throws(() => buildManifest([...files, files[0]], key, keyId, generatedAt), /duplicate/);

const tamperedFiles = files.map((file) => (
  file.path === "alpha.txt" ? { ...file, bytes: Buffer.from("tampered\n") } : file
));
assert.throws(() => verifyManifest(manifest, tamperedFiles, key, keyId), /verification failed/);

const tamperedMetadata = { ...manifest, generated_at: "2026-10-03T00:00:01.000Z" };
assert.throws(() => verifyManifest(tamperedMetadata, files, key, keyId), /verification failed/);
const tamperedContract = { ...manifest, node_encoding: "ambiguous" };
assert.throws(() => verifyManifest(tamperedContract, files, key, keyId), /encoding contract mismatch/);

const repository = mkdtempSync(join(tmpdir(), "opl-sha3-tree-"));
const commandPath = fileURLToPath(new URL("./sha3-tree.mjs", import.meta.url));
const gitEnvironment = { ...process.env };
for (const name of Object.keys(gitEnvironment)) {
  const normalized = name.toUpperCase();
  if (normalized === "OPL_A2A_HMAC_KEY_B64" || normalized === "OPL_A2A_HMAC_KEY_DPAPI_B64") {
    delete gitEnvironment[name];
  }
}
const commandEnvironment = {
  ...gitEnvironment,
  OPL_A2A_HMAC_KEY_B64: key.toString("base64"),
  OPL_A2A_HMAC_KEY_ID: keyId,
};
let testCount = 16;

function assertBuildRejected(repositoryPath, expected) {
  let failure;
  try {
    execFileSync(process.execPath, [commandPath, "build"], {
      cwd: repositoryPath,
      env: commandEnvironment,
      stdio: "pipe",
    });
  } catch (error) {
    failure = error;
  }
  assert.ok(failure);
  const stderr = Buffer.isBuffer(failure.stderr) ? failure.stderr.toString("utf8") : "";
  assert.match(`${failure.message}\n${stderr}`, expected);
  testCount += 1;
}

function assertModeRejected(mode, filePath) {
  const modeRepository = mkdtempSync(join(tmpdir(), "opl-sha3-tree-mode-"));
  try {
    execFileSync("git", ["init", "--quiet", modeRepository], { env: gitEnvironment });
    const objectId = execFileSync("git", ["-C", modeRepository, "hash-object", "-w", "--stdin"], {
      encoding: "utf8",
      env: gitEnvironment,
      input: "target\n",
    }).trim();
    execFileSync("git", [
      "-C",
      modeRepository,
      "update-index",
      "--add",
      "--cacheinfo",
      mode,
      objectId,
      filePath,
    ], { env: gitEnvironment });
    assertBuildRejected(modeRepository, new RegExp(`unsupported git mode ${mode}`));
  } finally {
    rmSync(modeRepository, { recursive: true, force: true });
  }
}

try {
  execFileSync("git", ["init", "--quiet", repository], { env: gitEnvironment });
  mkdirSync(join(repository, "nested"));
  assert.throws(
    () => execFileSync(process.execPath, [commandPath, "build"], {
      cwd: join(repository, "nested"),
      env: commandEnvironment,
      stdio: "pipe",
    }),
    /run from the Git repository root/,
  );
  writeFileSync(join(repository, "data.txt"), "staged\n");
  execFileSync("git", ["-C", repository, "add", "data.txt"], { env: gitEnvironment });
  execFileSync(process.execPath, [commandPath, "build"], {
    cwd: repository,
    env: commandEnvironment,
  });
  execFileSync("git", ["-C", repository, "add", "attest-hmac-sha3-512.json"], {
    env: gitEnvironment,
  });
  writeFileSync(join(repository, "data.txt"), "worktree-only\n");
  writeFileSync(join(repository, "attest-hmac-sha3-512.json"), "{}\n");
  execFileSync(process.execPath, [commandPath, "verify"], {
    cwd: repository,
    env: commandEnvironment,
  });
  execFileSync("git", ["-C", repository, "add", "data.txt"], { env: gitEnvironment });
  assert.throws(
    () => execFileSync(process.execPath, [commandPath, "verify"], {
      cwd: repository,
      env: commandEnvironment,
      stdio: "pipe",
    }),
  );
} finally {
  rmSync(repository, { recursive: true, force: true });
}

assertModeRejected("120000", "link");
assertModeRejected("160000", "submodule");

const unmergedRepository = mkdtempSync(join(tmpdir(), "opl-sha3-tree-unmerged-"));
try {
  execFileSync("git", ["init", "--quiet", unmergedRepository], { env: gitEnvironment });
  const objectId = execFileSync("git", ["-C", unmergedRepository, "hash-object", "-w", "--stdin"], {
    encoding: "utf8",
    env: gitEnvironment,
    input: "conflict\n",
  }).trim();
  const entries = [1, 2, 3]
    .map((stage) => `100644 ${objectId} ${stage}\tconflict.txt\n`)
    .join("");
  execFileSync("git", ["-C", unmergedRepository, "update-index", "--index-info"], {
    env: gitEnvironment,
    input: entries,
  });
  assertBuildRejected(unmergedRepository, /unmerged index entry/);
} finally {
  rmSync(unmergedRepository, { recursive: true, force: true });
}

const invalidPathRepository = mkdtempSync(join(tmpdir(), "opl-sha3-tree-path-"));
try {
  execFileSync("git", ["init", "--quiet", invalidPathRepository], { env: gitEnvironment });
  const objectId = execFileSync("git", ["-C", invalidPathRepository, "hash-object", "-w", "--stdin"], {
    encoding: "utf8",
    env: gitEnvironment,
    input: "invalid path\n",
  }).trim();
  const entry = Buffer.concat([
    Buffer.from(`100644 ${objectId}\tbad-`, "ascii"),
    Buffer.from([0xff]),
    Buffer.from(".txt\n", "ascii"),
  ]);
  execFileSync("git", ["-C", invalidPathRepository, "update-index", "--index-info"], {
    env: gitEnvironment,
    input: entry,
  });
  assertBuildRejected(invalidPathRepository, /non-UTF-8 git paths are not supported/);
} finally {
  rmSync(invalidPathRepository, { recursive: true, force: true });
}

if (process.platform === "win32") {
  const caseRepository = mkdtempSync(join(tmpdir(), "opl-sha3-tree-case-"));
  try {
    execFileSync("git", ["init", "--quiet", caseRepository], { env: gitEnvironment });
    writeFileSync(join(caseRepository, "ATTEST-HMAC-SHA3-512.JSON"), "{}\n");
    execFileSync("git", ["-C", caseRepository, "add", "ATTEST-HMAC-SHA3-512.JSON"], {
      env: gitEnvironment,
    });
    assertBuildRejected(caseRepository, /manifest path case conflict/);
  } finally {
    rmSync(caseRepository, { recursive: true, force: true });
  }
}

console.log(JSON.stringify({ ok: true, tests: testCount }));

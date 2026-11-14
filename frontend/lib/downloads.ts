// Cloudflare caches the agent files for hours under the same name, so each build's links
// carry a hash of the files (set in next.config.mjs). A new agent gets a new URL.
const v = process.env.NEXT_PUBLIC_AGENT_VERSION
const tag = v ? `?v=${v}` : ""

export const AGENT_INSTALLER = `/downloads/LabhyaComputeAgentSetup.exe${tag}`
export const AGENT_PORTABLE = `/downloads/LabhyaComputeAgent.exe${tag}`

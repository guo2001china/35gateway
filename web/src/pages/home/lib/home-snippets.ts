import { getApi35Base } from "@/api/api35";
import { stringifyJson } from "./home-utils";

export function buildCurlSnippet(endpoint: string, body: Record<string, unknown>, chain: string) {
  const chainHeader = chain.trim() ? ` \\\n  -H "x-api35-chain: ${chain.trim()}"` : "";
  return `curl -X POST "${getApi35Base()}${endpoint}" \\\n  -H "Authorization: Bearer $API35_API_KEY" \\\n  -H "Content-Type: application/json"${chainHeader} \\\n  -d '${JSON.stringify(body, null, 2)}'`;
}

export function buildPythonSnippet(endpoint: string, body: Record<string, unknown>, chain: string) {
  const extraHeaders = chain.trim() ? `\nheaders["x-api35-chain"] = "${chain.trim()}"` : "";
  return `import requests\n\nheaders = {\n    "Authorization": "Bearer " + API35_API_KEY,\n    "Content-Type": "application/json",\n}${extraHeaders}\n\nresponse = requests.post(\n    "${getApi35Base()}${endpoint}",\n    headers=headers,\n    json=${stringifyJson(body)},\n    timeout=120,\n)\nprint(response.status_code)\nprint(response.json())`;
}

export function buildJavaScriptSnippet(endpoint: string, body: Record<string, unknown>, chain: string) {
  const extraHeaders = chain.trim() ? `,\n    "x-api35-chain": "${chain.trim()}"` : "";
  return `const response = await fetch("${getApi35Base()}${endpoint}", {\n  method: "POST",\n  headers: {\n    "Authorization": \`Bearer \${API35_API_KEY}\`,\n    "Content-Type": "application/json"${extraHeaders}\n  },\n  body: JSON.stringify(${stringifyJson(body)})\n});\n\nconst data = await response.json();\nconsole.log(response.status, data);`;
}

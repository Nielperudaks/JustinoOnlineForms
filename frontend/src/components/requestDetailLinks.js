const SAFE_LINK_PROTOCOLS = new Set(["http:", "https:", "mailto:", "tel:"]);

export function getRequestFieldType(request, fieldName) {
  const field = (request?.form_fields || []).find((item) => item.name === fieldName);
  return field?.type || "";
}

export function getSafeLinkHref(value) {
  const rawValue = String(value ?? "").trim();
  if (!rawValue) return "";

  const candidate = /^[a-z][a-z\d+.-]*:/i.test(rawValue)
    ? rawValue
    : `https://${rawValue}`;

  try {
    const url = new URL(candidate);
    return SAFE_LINK_PROTOCOLS.has(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
}

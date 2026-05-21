import { getRequestFieldType, getSafeLinkHref } from "./requestDetailLinks";

describe("request detail link fields", () => {
  test("finds field types from the saved request field snapshot", () => {
    const request = {
      form_fields: [
        { name: "reference_url", type: "link" },
        { name: "purpose", type: "text" },
      ],
    };

    expect(getRequestFieldType(request, "reference_url")).toBe("link");
    expect(getRequestFieldType(request, "purpose")).toBe("text");
    expect(getRequestFieldType(request, "missing")).toBe("");
  });

  test("normalizes safe link URLs for anchor hrefs", () => {
    expect(getSafeLinkHref("example.com/path")).toBe("https://example.com/path");
    expect(getSafeLinkHref("https://example.com/path")).toBe("https://example.com/path");
    expect(getSafeLinkHref("mailto:support@example.com")).toBe("mailto:support@example.com");
    expect(getSafeLinkHref("javascript:alert(1)")).toBe("");
  });
});

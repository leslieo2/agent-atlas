import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DatasetUpload } from "@/src/features/dataset-upload/DatasetUpload";

describe("DatasetUpload", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("prefers showPicker when the browser exposes it", () => {
    const showPicker = vi.fn();
    Object.defineProperty(HTMLInputElement.prototype, "showPicker", {
      configurable: true,
      value: showPicker
    });

    render(<DatasetUpload fileInputRef={{ current: null }} onChange={vi.fn(async () => undefined)} />);

    fireEvent.click(screen.getByRole("button", { name: "Upload JSONL" }));

    expect(showPicker).toHaveBeenCalledTimes(1);
  });

  it("falls back to click when showPicker throws", () => {
    const clickSpy = vi.spyOn(HTMLInputElement.prototype, "click").mockImplementation(() => undefined);
    Object.defineProperty(HTMLInputElement.prototype, "showPicker", {
      configurable: true,
      value: vi.fn(() => {
        throw new DOMException("showPicker failed", "NotAllowedError");
      })
    });

    render(<DatasetUpload fileInputRef={{ current: null }} onChange={vi.fn(async () => undefined)} />);

    fireEvent.click(screen.getByRole("button", { name: "Upload JSONL" }));

    expect(clickSpy).toHaveBeenCalledTimes(1);
  });

  it("falls back to click when showPicker is unavailable", () => {
    Object.defineProperty(HTMLInputElement.prototype, "showPicker", {
      configurable: true,
      value: undefined
    });
    const clickSpy = vi.spyOn(HTMLInputElement.prototype, "click").mockImplementation(() => undefined);

    render(<DatasetUpload fileInputRef={{ current: null }} onChange={vi.fn(async () => undefined)} />);

    fireEvent.click(screen.getByRole("button", { name: "Upload JSONL" }));

    expect(clickSpy).toHaveBeenCalledTimes(1);
  });
});

import { useMemo } from "react";
import type { FileTypeDetectionResult } from "../types/fileViewer.types";
import { detectFileType } from "../utils/fileTypeUtils";

/**
 * Hook to detect file type from filename and content type
 */
export function useFileTypeDetection(
	filename: string,
	contentType: "text" | "base64",
): FileTypeDetectionResult {
	return useMemo(() => {
		return detectFileType(filename, contentType);
	}, [filename, contentType]);
}

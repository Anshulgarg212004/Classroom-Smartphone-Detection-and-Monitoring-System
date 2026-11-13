
import { apiRequest } from "./api";

export async function getDetections(token, classroomId = "") {
  const query = classroomId
    ? `?classroom_id=${encodeURIComponent(classroomId)}`
    : "";

  const data = await apiRequest(
    `/api/detections/${query}`,
    {},
    token
  );

  // API agar seedha array return kare ya detections object de,
  // dono formats ko handle karne ki koshish.
  if (Array.isArray(data)) {
    return data;
  }

  return data.detections || data.data || [];
}


import api from "../api/axios";

const LAPTOP_CAMERA_ID = "laptop-camera-1";

export async function getClassrooms() {
  const response = await api.get("/classrooms/");
  return response.data.classrooms || [];
}

export async function startClassroomMonitoring(classroomId) {
  const response = await api.post("/monitoring/start", {
    cameras: [
      {
        camera_id: LAPTOP_CAMERA_ID,
        classroom_id: Number(classroomId),
        name: "Laptop Webcam",
        source_type: "webcam",
        source: 0
      }
    ]
  });

  return response.data;
}

export async function stopClassroomMonitoring() {
  const response = await api.post("/monitoring/stop", {
    camera_id: LAPTOP_CAMERA_ID
  });

  return response.data;
}

export async function getMonitoringStatus() {
  const response = await api.get("/monitoring/status");
  return response.data.monitoring;
}

export async function getMonitoringFrame() {
  const response = await api.get("/monitoring/frame", {
    params: {
      camera_id: LAPTOP_CAMERA_ID
    },
    responseType: "blob"
  });

  return URL.createObjectURL(response.data);
}

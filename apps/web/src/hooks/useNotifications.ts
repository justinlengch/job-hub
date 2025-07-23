import { useState, useCallback } from "react";

interface NotificationState {
  id: string;
  message: string;
  type: "success" | "error";
}

export const useNotifications = () => {
  const [notifications, setNotifications] = useState<NotificationState[]>([]);

  const addNotification = useCallback(
    (message: string, type: "success" | "error") => {
      const id = Date.now().toString();
      setNotifications((prev) => [...prev, { id, message, type }]);
    },
    []
  );

  const removeNotification = useCallback((id: string) => {
    setNotifications((prev) =>
      prev.filter((notification) => notification.id !== id)
    );
  }, []);

  return {
    notifications,
    addNotification,
    removeNotification,
  };
};

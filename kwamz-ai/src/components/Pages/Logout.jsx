import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

const Logout = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Clear auth data
    localStorage.removeItem("token");
    sessionStorage.clear(); // optional

    // Redirect to login
    navigate("/");
  }, [navigate]);
  
  return null; // or a spinner/message if needed
};

export default Logout;

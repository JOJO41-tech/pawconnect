import mysql from "mysql2/promise";

const pool = mysql.createPool({
  host: "localhost",
  port: 3307,
  user: "root",
  password: "Pyitheinkyaw123",
  database: "pawconnect",
});

export default pool;
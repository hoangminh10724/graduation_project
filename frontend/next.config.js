/** @type {import('next').NextConfig} */
module.exports = process.platform === "win32" ? {} : { output: "standalone" };

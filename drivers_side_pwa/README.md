# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react/README.md) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Driver map traffic API

- Start the dedicated frontend API: `python api/frontend_map_api.py` (exposes `/pwa/traffic/recent` on port 8010 by default).
- Point the PWA to it by setting `VITE_API_BASE=http://localhost:8010` in `.env` (or leave blank if you reverse-proxy).
- Run the app: `cd drivers_side_pwa && npm install && npm run dev`.

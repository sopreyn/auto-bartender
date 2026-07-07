# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.

## Running the App Locally

This project has two parts: a Python (Flask) backend that handles face/age/gender detection, and a React (Vite) frontend.

### Prerequisites
- Python 3.9+
- Node.js 18+
- The backend also needs the Caffe model files (`deploy_gender2.prototxt`, `gender_net.caffemodel`, `deploy_age2.prototxt`, `age_net.caffemodel`) present in the `backend` folder.

### 1. Backend setup

```bash
cd backend
pip install -r requirements.txt
python main.py
```

The Flask server will start on `http://127.0.0.1:5000`.

### 2. Frontend setup

In a separate terminal, from the project root:

```bash
npm install
npm run dev
```

### 3. Open the app

Visit [http://localhost:5173](http://localhost:5173) in your browser. The React app will connect to the local Flask backend for frame processing.

> **Note:** Both the backend and frontend need to be running simultaneously — the backend in its own terminal (`backend` folder), and the frontend in the root project folder.
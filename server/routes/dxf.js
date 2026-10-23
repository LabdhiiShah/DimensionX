const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { exec } = require('child_process');
// const pool = require('../db'); // Uncomment if saving paths to DB later

const router = express.Router();

// 1. Ensure local uploads folder exists
const UPLOAD_DIR = path.join(__dirname, '..', 'uploads');
if (!fs.existsSync(UPLOAD_DIR)) {
  fs.mkdirSync(UPLOAD_DIR, { recursive: true });
}

// 2. Configure Multer (Storage Engine)
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, UPLOAD_DIR);
  },
  filename: (req, file, cb) => {
    // Save as: projectId_timestamp.dxf
    const projectId = req.body.projectId || 'temp';
    cb(null, `${projectId}_${Date.now()}.dxf`);
  }
});

// File filter to ensure only DXF is uploaded
const upload = multer({ 
  storage,
  fileFilter: (req, file, cb) => {
    if (path.extname(file.originalname).toLowerCase() !== '.dxf') {
      return cb(new Error('Only .dxf files are allowed'));
    }
    cb(null, true);
  },
  limits: { fileSize: 20 * 1024 * 1024 } // 20MB limit (matches frontend)
});

// 3. The Upload & Process Route
router.post('/upload', upload.single('dxfFile'), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No file uploaded.' });
  }

  const projectId = req.body.projectId || 'temp';
  const dxfPath = req.file.path;
  
  // Define paths for the output files
  const projectOutputDir = path.join(UPLOAD_DIR, projectId);
  if (!fs.existsSync(projectOutputDir)) {
    fs.mkdirSync(projectOutputDir, { recursive: true });
  }

  const jsonPath = path.join(projectOutputDir, 'architecture.json');
  const glbDir = projectOutputDir;

  // Clean up any old GLB files in this folder before generating a new one
  // This prevents accidentally returning a previous model if the new one fails
  const existingFiles = fs.readdirSync(glbDir);
  existingFiles.forEach(file => {
    if (file.endsWith('.glb') || file.endsWith('.obj') || file.endsWith('.mtl')) {
      fs.unlinkSync(path.join(glbDir, file));
    }
  });

  // --- Points to the root-level dxf_parser folder ---
  const pythonExe = 'python'; 
  const dxfParserDir = path.join(__dirname, '..', '..', 'dxf_parser'); 
  const jsonScript = path.join(dxfParserDir, 'dimensionx_dxf_to_json.py');
  const exportScript = path.join(dxfParserDir, 'export_3d.py');

  console.log(`[DXF Pipeline] Processing ${req.file.originalname}...`);

  // Step A: Run DXF -> JSON (Validation & Parsing)
  const cmdJson = `${pythonExe} "${jsonScript}" "${dxfPath}" --output "${jsonPath}"`;
  
  exec(cmdJson, { cwd: dxfParserDir }, (err, stdout, stderr) => {
    if (err) {
      console.error('[DXF Pipeline] JSON Gen Failed:', stderr || err.message);
      return res.status(400).json({ 
        error: 'DXF Validation failed. Please ensure the file follows the standard layers.',
        details: stderr
      });
    }

    console.log(`[DXF Pipeline] JSON generated. Running 3D export...`);

    // Step B: Run JSON -> GLB (3D Generation)
    const cmdGlb = `${pythonExe} "${exportScript}" "${jsonPath}" "${glbDir}"`;
    
    exec(cmdGlb, { cwd: dxfParserDir }, (err2, stdout2, stderr2) => {
      if (err2) {
        console.error('[DXF Pipeline] GLB Gen Failed:', stderr2 || err2.message);
        return res.status(500).json({ 
          error: 'Failed to generate 3D model from DXF.',
          details: stderr2
        });
      }

      // Dynamically find the generated GLB file (it might be named 1BHK_01.glb, etc.)
      const filesInDir = fs.readdirSync(glbDir);
      const glbFile = filesInDir.find(f => f.endsWith('.glb'));

      if (!glbFile) {
         return res.status(500).json({ error: 'Pipeline finished but no GLB file was generated.' });
      }

      const finalGlbPath = path.join(glbDir, glbFile);
      
      // Create a URL for the frontend to access via HTTP
      const glbUrl = `/uploads/${projectId}/${glbFile}`;

      console.log(`[DXF Pipeline] Success! Generated: ${glbFile}`);

      res.json({
        success: true,
        message: 'DXF Processed successfully',
        glbPath: finalGlbPath,
        jsonPath: jsonPath,
        glbUrl: glbUrl 
      });
    });
  });
});

module.exports = router;
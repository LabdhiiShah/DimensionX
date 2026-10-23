const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { exec } = require('child_process');
const util = require('util');
const execPromise = util.promisify(exec);
const db = require('../db');

const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    const projectId = req.body.projectId || 'unknown';
    const dir = path.join(__dirname, '..', 'uploads', String(projectId));
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    cb(null, dir);
  },
  filename: function (req, file, cb) {
    cb(null, file.originalname);
  }
});

const upload = multer({ 
  storage: storage,
  limits: { fileSize: 20 * 1024 * 1024 },
  fileFilter: (req, file, cb) => {
    if (path.extname(file.originalname).toLowerCase() !== '.dxf') {
      return cb(new Error('Only .dxf files are allowed'));
    }
    cb(null, true);
  }
});

router.post('/upload', upload.single('dxfFile'), async (req, res) => {
  try {
    const { projectId } = req.body;
    const file = req.file;

    if (!file) return res.status(400).json({ error: 'Please upload a file' });
    if (!projectId || projectId === 'temp_project' || projectId === 'undefined') {
      return res.status(400).json({ error: 'Valid projectId is required.' });
    }

    const projectFolder = path.join(__dirname, '..', 'uploads', String(projectId));
    const absoluteDxfPath = path.join(projectFolder, file.filename);
    const relativeDxfPath = `/uploads/${projectId}/${file.filename}`;
    const baseName = path.parse(file.filename).name; // e.g., "1BHK_09"

    await db.query(`UPDATE projects SET dxf_file_path = $1 WHERE id = $2`, [relativeDxfPath, projectId]);

    console.log("1. Generating JSON from DXF...");
    // Run Python to generate JSON
    await execPromise(`python ../dxf_parser/dimensionx_dxf_to_json.py "${absoluteDxfPath}"`);
    
    const expectedJsonPath = path.join(projectFolder, `${baseName}_architecture.json`);
    
    if (!fs.existsSync(expectedJsonPath)) {
        throw new Error("Python script did not generate the JSON file.");
    }

    console.log("2. Generating GLB from JSON...");
    // Run Python to generate GLB (Pass the JSON path and the output directory)
    await execPromise(`python ../dxf_parser/export_3d.py "${expectedJsonPath}" "${projectFolder}"`);

    const expectedGlbPath = path.join(projectFolder, `${baseName}.glb`);
    
    let glbUrl = null;
    let parsedPlan = null;
    let jsonPath = `/uploads/${projectId}/${baseName}_architecture.json`;

    // Read the JSON for the database
    const jsonContent = fs.readFileSync(expectedJsonPath, 'utf8');
    parsedPlan = JSON.parse(jsonContent);

    if (fs.existsSync(expectedGlbPath)) {
      glbUrl = `/uploads/${projectId}/${baseName}.glb`;
      console.log("✅ GLB generated successfully:", glbUrl);
    } else {
      throw new Error("GLB generation failed.");
    }

    // Cleanup: Delete unwanted files (obj, mtl, etc.)
    const files = fs.readdirSync(projectFolder);
    files.forEach(f => {
      const ext = path.extname(f).toLowerCase();
      if (!['.dxf', '.glb', '.json'].includes(ext)) {
        fs.unlinkSync(path.join(projectFolder, f));
        console.log(`Deleted unwanted file: ${f}`);
      }
    });

    // Update Database
    const updateQuery = `
      UPDATE projects 
      SET glb_url = $1, plan = $2
      WHERE id = $3 
      RETURNING *;
    `;
    
    const result = await db.query(updateQuery, [
      glbUrl, 
      parsedPlan ? JSON.stringify(parsedPlan) : null,
      projectId
    ]);

    res.status(200).json({ 
      message: 'Processed successfully', 
      project: result.rows[0],
      glbUrl: glbUrl,
      jsonPath: jsonPath 
    });

  } catch (error) {
    console.error("❌ Server error:", error);
    res.status(500).json({ error: 'Processing failed', details: error.message });
  }
});

module.exports = router;
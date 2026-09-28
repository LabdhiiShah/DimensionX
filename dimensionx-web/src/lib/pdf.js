import { jsPDF } from 'jspdf';
import { typeNameFor } from '../data/catalog.js';

// Builds the "build sheet": a full top-down floor plan picture + a schedule
// of every placed piece (type, style, position, rotation, scale, size).
export function downloadDesignPdf(items, floorPlanSrc) {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'pt', format: 'a4' });
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 40;
  let y = margin;
  const list = items || [];

  doc.setFont('helvetica', 'bold'); doc.setFontSize(18);
  doc.text('DimensionX - Design Build Sheet', margin, y); y += 22;
  doc.setFont('helvetica', 'normal'); doc.setFontSize(10); doc.setTextColor(90);
  doc.text('Generated ' + new Date().toLocaleString(), margin, y); y += 24;
  doc.setTextColor(20);

  doc.setFont('helvetica', 'bold'); doc.setFontSize(12);
  doc.text('Floor Plan (top view)', margin, y); y += 8;
  if (floorPlanSrc) {
    const w = pageWidth - margin * 2;
    const h = w * 9 / 16;
    doc.addImage(floorPlanSrc, 'JPEG', margin, y + 6, w, h);
    y += h + 22;
  } else {
    doc.setFont('helvetica', 'italic'); doc.setFontSize(10);
    doc.text('(Floor plan capture was unavailable - connect to Unity and try again.)', margin, y + 14);
    y += 30;
  }

  doc.setFont('helvetica', 'bold'); doc.setFontSize(12);
  doc.text('Furniture Schedule (' + list.length + ' item' + (list.length !== 1 ? 's' : '') + ')', margin, y); y += 16;

  const cols = [
    { label: '#', width: 22 }, { label: 'Type', width: 78 }, { label: 'Style', width: 82 },
    { label: 'Position (x, y, z)', width: 118 }, { label: 'Rotation', width: 52 },
    { label: 'Scale', width: 56 }, { label: 'Size', width: 50 },
  ];
  const drawHeader = () => {
    doc.setFont('helvetica', 'bold'); doc.setFontSize(9);
    let x = margin;
    cols.forEach(c => { doc.text(c.label, x, y); x += c.width; });
    y += 6; doc.setDrawColor(210); doc.line(margin, y, pageWidth - margin, y); y += 12;
    doc.setFont('helvetica', 'normal');
  };
  drawHeader();

  if (list.length === 0) {
    doc.setFont('helvetica', 'italic'); doc.setFontSize(10);
    doc.text('No furniture has been placed yet.', margin, y);
    y += 18;
  }
  list.forEach((inst, i) => {
    if (y > pageHeight - margin) { doc.addPage(); y = margin; drawHeader(); }
    const n = (v, d) => Number(v ?? 0).toFixed(d);
    const cells = [
      String(i + 1),
      typeNameFor(inst.type_id),
      inst.style_name || '-',
      '(' + n(inst.world_x, 2) + ', ' + n(inst.world_y, 2) + ', ' + n(inst.world_z, 2) + ')',
      n(inst.rotation_y_deg, 0) + ' deg',
      n(inst.scale ?? 1, 2) + ' u',
      Math.round((inst.scale_multiplier ?? 1) * 100) + '%',
    ];
    let x = margin;
    cells.forEach((val, ci) => { doc.text(String(val), x, y); x += cols[ci].width; });
    y += 18;
  });

  doc.setFont('helvetica', 'italic'); doc.setFontSize(8); doc.setTextColor(120);
  doc.text("Scale = raw local-scale units (exact rebuild value) | Size = % of that piece's original imported size.", margin, y + 4);

  doc.save('dimensionx-design-' + new Date().toISOString().slice(0, 10) + '.pdf');
}

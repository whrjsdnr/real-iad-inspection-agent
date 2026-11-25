/** Approximate family templates, visually checked against dataset C1 references.
 * Dimensions are display units, never metrology. Regions are stable visual IDs,
 * not proof of ROI correspondence. Existing toothbrush/toy IDs are preserved. */
export type Family = 'connector' | 'disc' | 'ring' | 'frame' | 'block' | 'board' | 'brush' | 'bead' | 'zipper'
export type MaterialKind = 'plastic' | 'metal' | 'rubber' | 'board' | 'wood' | 'ceramic' | 'contact'
export interface ProductTemplate {
  family: Family
  size: [number, number, number]
  material: MaterialKind
  hole?: number
  ribs?: number
  pins?: number
  form?: string
}
export const PRODUCT_TEMPLATES: Record<string, ProductTemplate> = {
  audiojack: {family:'connector',size:[1.5,.65,1],material:'rubber',pins:5,form:'jack'},
  bottle_cap: {family:'disc',size:[1.6,.28,1.6],material:'plastic',ribs:32,form:'cap'},
  button_battery: {family:'disc',size:[1.6,.16,1.6],material:'metal',form:'battery'},
  end_cap: {family:'frame',size:[1.7,.25,1.7],material:'rubber',hole:.18,form:'square'},
  eraser: {family:'block',size:[1.8,.45,1.1],material:'rubber',form:'eraser'},
  fire_hood: {family:'disc',size:[1.6,.4,1.6],material:'wood',form:'dome'},
  mint: {family:'ring',size:[1.6,.24,1.6],material:'ceramic',hole:.3,ribs:16},
  mounts: {family:'frame',size:[1.6,.5,1.4],material:'plastic',hole:.25,form:'rails'},
  pcb: {family:'board',size:[1.5,.08,1.6],material:'board',pins:4,form:'pcb'},
  phone_battery: {family:'block',size:[1.4,.18,1.9],material:'rubber',pins:3,form:'battery'},
  plastic_nut: {family:'ring',size:[1.5,.5,1.5],material:'rubber',hole:.4,ribs:6,form:'nut'},
  plastic_plug: {family:'ring',size:[1.6,.36,1.6],material:'plastic',hole:.28,form:'plug'},
  porcelain_doll: {family:'ring',size:[1.6,.35,1.6],material:'ceramic',hole:.52,form:'smooth'},
  regulator: {family:'disc',size:[1.6,.24,1.6],material:'plastic',ribs:8,form:'regulator'},
  rolled_strip_base: {family:'frame',size:[1.6,.3,1.6],material:'plastic',hole:.12,form:'pyramid'},
  sim_card_set: {family:'frame',size:[1.5,.07,1.9],material:'contact',hole:.46,form:'sim'},
  switch: {family:'connector',size:[1.1,.9,1.1],material:'rubber',pins:2,form:'switch'},
  tape: {family:'ring',size:[1.7,.6,1.7],material:'wood',hole:.63,form:'tape'},
  terminalblock: {family:'connector',size:[2,.7,.75],material:'plastic',pins:6,form:'terminal'},
  toothbrush: {family:'brush',size:[.52,3.5,.25],material:'plastic'},
  toy: {family:'disc',size:[1.8,.65,1.8],material:'plastic',ribs:10,form:'toy'},
  toy_brick: {family:'block',size:[1.7,.6,1.5],material:'wood',form:'brick'},
  transistor1: {family:'board',size:[1.7,.3,.8],material:'rubber',pins:16,form:'chip'},
  u_block: {family:'ring',size:[1.6,.35,1.6],material:'ceramic',hole:.62,form:'plain'},
  usb: {family:'connector',size:[1.3,.55,1.7],material:'metal',pins:4,form:'usb'},
  usb_adaptor: {family:'connector',size:[1.1,.7,1.8],material:'rubber',pins:4,form:'adapter'},
  vcpill: {family:'disc',size:[1.5,.5,1.15],material:'ceramic',form:'pill'},
  wooden_beads: {family:'bead',size:[1.4,1.4,1.4],material:'wood',hole:.22},
  woodstick: {family:'disc',size:[1.6,1.2,1.6],material:'wood',form:'stick'},
  zipper: {family:'zipper',size:[.8,.18,3],material:'metal',ribs:18},
}

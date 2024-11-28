/** @odoo-module **/

import { formView } from '@web/views/form/form_view'
import { registry } from "@web/core/registry"
import { FormPickLocationRender } from './pick_location_barcode'
//JsClassBarcodePurchase constant is added to views registry
export const JsClassBarcodePickLocation = {
   ...formView,
   Controller: FormPickLocationRender,
};
registry.category("views").add("pick_location_barcode_js_class", JsClassBarcodePickLocation);

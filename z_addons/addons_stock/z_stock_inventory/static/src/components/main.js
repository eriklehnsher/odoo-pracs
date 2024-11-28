/** @odoo-module **/

import BarcodeStockInventoryModel from '@z_stock_inventory/models/barcode_stock_inventory_model';
import MainComponent from '@stock_barcode/components/main';

import { patch } from "@web/core/utils/patch";

patch(MainComponent.prototype, {

    _getModel() {
        const { resId, resModel, rpc, notification, orm, action } = this;
        if (this.resModel === 'stock.inventory') {
            return new BarcodeStockInventoryModel(resModel, resId, { rpc, notification, orm, action });
        }
        return super._getModel(...arguments);
    },

    saveFormView(lineRecord) {
        const lineId = (lineRecord && lineRecord.resId) || (this._editedLineParams && this._editedLineParams.currentId)
        let recordId = (lineRecord.resModel === this.resModel) ? lineId : undefined
        if (lineRecord.resModel == 'stock.quant') {
            recordId = lineRecord.resId
        }
        this._onRefreshState({ recordId, lineId })
    }
});


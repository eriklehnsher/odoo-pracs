/** @odoo-module */

import {patch} from "@web/core/utils/patch";
import {StockBarcodeKanbanController} from '@stock_barcode/kanban/stock_barcode_kanban_controller';

patch(StockBarcodeKanbanController.prototype, {
    async createRecord() {
        if (this.props.resModel === 'stock.inventory') {
            const action = await this.model.orm.call(
                'stock.inventory',
                'open_new_stock_inventory',
                [], {context: this.props.context}
            );
            if (action) {
                return this.actionService.doAction(action);
            }
        }
        return super.createRecord(...arguments);
    }
});

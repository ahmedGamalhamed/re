const { ProductModel, AffiliateModel } = require('../model')
const { WEB_SERVER_URL } = require('../config/config'); 

let redirectUrl = async (req, res) => {
    await ProductModel.findOne({
        prod_shortcode: req.params.shortcode
    }, (err, product) => {
        if (err) {
            res.status(404).send("can not find product!")
        }
        if (product) {
            AffiliateModel.findOne({storename: product.prod_site}, (err, result) => {
                if (err) {
                    res.status(404).send("can not find product!")
                }
                if (result){
                    let merged_url = ""
                    if ( result.affiliate.includes("awin1.com")) {
                        merged_url = result.affiliate + "[[" + product.prod_url + "]]"
                    }
                    else {
                        merged_url = result.affiliate + product.prod_url 
                    }
                    res.status(301).redirect(merged_url)
                }
                else {
                    res.status(304).redirect(WEB_SERVER_URL)
                }
            })
        }
        else {
            res.status(304).redirect(WEB_SERVER_URL)
        }
    })
}

module.exports = {
    redirectUrl
}
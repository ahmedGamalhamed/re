let mongoose = require('mongoose')
const bcrypt = require('bcrypt');
let Schema = mongoose.Schema

const saltRounds = 10;

let Product = new Schema({
    _id: { type: String },
    prod_id: { type: String },
    prod_name: { type: String },
    prod_url: { type: String },
    prod_image: { type: String },
    prod_status: { type: String },
    prod_sale: { type: Boolean },
    prod_size: { type: Array },
    prod_price: { type: String },
    prod_oldprice: { type: String },
    prod_site: { type: String },
    prod_updatedtime: { type: String },
    is_favorite: { type: Boolean },
    prod_upvotes: { type: Number }
}, {
    collection: 'products'
})

let Keyword = new Schema({
    keyword: { type: String, required: true },
    keyAlias: { type: String, required: true }
}, { collection: 'filters' })

let Affiliate = new Schema({
    storename: { type: String, required: true },
    affiliate: { type: String, required: true }
}, { collection: 'affiliates' })

let UserSchema = new Schema({
    name: { type: String, required: true },
    email: { type: String, required: true },
    password: { type: String, required: true },
    date: { type: Date, default: Date.now },
    role: { type: String, default: "admin" },
    isAllowed: { type: Number, default: 0 }
}, { collection: 'user' })

let Discount = new Schema({
    storename: { type: String, required: true },
    discount_profit: { type: Number, required: true },
    discount_code: { type: String, required: true },
    apply: { type: String, required: true },
    expireDatetime: { type: Date, required: true },
}, { collection: 'discount' })

let Instagram = new Schema({
    username : {type: String, required: true},
    type: {type: String, required: true},
    caption: {type: String, required: true},
    imgUrl : {type: String, required: true},
    isGallery : {type: Boolean, required: true},
    isVideo : {type: Boolean, required: true},
    postUrl: {type: String, required: true},
    postTime: {type: Date, required: true}
}, { collection: "instagram_posts"})

let ProductModel = mongoose.model('Product', Product)
let KeywordModel = mongoose.model('Keyword', Keyword)
let AffiliateModel = mongoose.model('Affiliate', Affiliate)
let UserModel = mongoose.model('User', UserSchema)
let DiscountModel = mongoose.model('Discount', Discount)
let InstagramModel = mongoose.model("Instagram", Instagram)


Affiliate.index({ storename: 1 }, { unique: true })
Affiliate.on('index', function(error) {
    console.log(error)
})

module.exports = {
    ProductModel,
    KeywordModel,
    AffiliateModel,
    UserModel,
    DiscountModel,
    InstagramModel
}
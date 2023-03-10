const express = require('express')
const passport = require('passport');

const ProductControl = require('../controllers/product-ctrl')
const KeywordControl = require('../controllers/keyword-ctrl')
const AffiliateControl = require('../controllers/affiliate-ctrl')
const ShortUrlControl = require('../controllers/shorturl-ctrl')
const UserControl = require("../controllers/user-ctrl")
const DiscountControl = require("../controllers/discount-ctrl")
const InstagramControl = require("../controllers/instagram-ctrl")

const router = express.Router()

router.post('/products', ProductControl.getProducts)
router.post('/products/uf', ProductControl.updateFavorite)
router.post('/products/uv', ProductControl.updateVotes)
router.get('/keywords', KeywordControl.getKeywords)
router.post('/keyword/add', KeywordControl.addKeyword)
router.get('/keyword/:id', KeywordControl.getKeywordbyId)
router.post('/keyword/update/:id', KeywordControl.updateKeyword)
router.delete('/keyword/delete/:id', KeywordControl.deleteKeyword)

router.get('/affiliates', AffiliateControl.getAffiliates)
router.post('/affiliate/add', AffiliateControl.addAffiliate)
router.get('/affiliate/:id', AffiliateControl.getAffiliatebyId)
router.post('/affiliate/update/:id', AffiliateControl.updateAffiliate)
router.delete('/affiliate/delete/:id', AffiliateControl.deleteAffiliate)

router.get('/product/:shortcode', ShortUrlControl.redirectUrl)

router.post('/register', UserControl.registerUser)
router.post('/login', UserControl.loginUser)
router.get('/me', passport.authenticate('jwt', { session: false }), UserControl.meAuth)


router.get('/discounts', DiscountControl.getDiscounts)
router.post('/discount/add', DiscountControl.addDiscount)
router.get('/discount/:id', DiscountControl.getDiscountbyId)
router.post('/discount/update/:id', DiscountControl.updateDiscount)
router.delete('/discount/delete/:id', DiscountControl.deleteDiscount)

router.post('/getInstapost', InstagramControl.getInstagramPosts)

module.exports = router
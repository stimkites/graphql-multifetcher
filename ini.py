import multiprocessing

BASE_URL = 'https://gql.tokopedia.com/graphql/'
SHOP_URL = 'https://www.tokopedia.com/'
CATEGORY_REQUEST = """
query headerMainData {
  categoryAllListLite {
   categories {
      id
      name
      url
      }
  }
}
"""
CATEGORY_REQUEST = """
query headerMainData {
  dynamicHomeIcon {
    categoryGroup {
      id
      title
      desc
      categoryRows {
        id
        name
        url
        imageUrl
        type
        categoryId
        __typename
      }
      __typename
    }
    __typename
  }
  categoryAllListLite {
    categories {
      id
      name
      url
      iconImageUrl
      isCrawlable
      children {
        id
        name
        url
        isCrawlable
        children {
          id
          name
          url
          isCrawlable
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
}
"""
PRODUCTS_REQUEST = """
query SearchProductQuery($params: String) {
  CategoryProducts: searchProduct(params: $params) {
    count
    data: products {
      id
      url
      imageUrl: image_url
      catId: category_id
      stock
      discount: discount_percentage
      preorder: is_preorder
      name
      price
      original_price
      rating
      shop {
        id
        url
        name
      }
          }
      }
  
}
"""
ROWS_COUNT = 60
PAGES_PER_THREAD = 10
MAX_CONCURRENCY = int(multiprocessing.cpu_count() / 2)
# MAX_CONCURRENCY = 4
NEED_TO_FETCH = 10000000
# NEED_TO_FETCH = 100
REQUESTS_TIMEOUT = 5
REQUESTS_DEBUG = False

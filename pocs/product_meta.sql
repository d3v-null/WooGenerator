SELECT 
    p.`ID`,
    MAX(CASE WHEN pm.`meta_key` = '_sku' THEN pm.`meta_value` ELSE "" END) as sku,
    p.`post_title` as title,
    MAX(CASE WHEN pm.`meta_key` = '_stock_status' THEN pm.`meta_value` ELSE "" END) as stock_status
FROM
    `tt6164_posts` p
    INNER JOIN `tt6164_postmeta` pm
    ON p.`ID` = pm.`post_id`
WHERE
    p.`post_type` = 'product'
    AND p.`post_status` = 'publish'
GROUP BY
    p.`ID`
    